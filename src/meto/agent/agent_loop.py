"""Main model/tool-calling loop.

This module owns the long-running loop that:
1) builds model messages (system + conversation history)
2) calls the LLM
3) executes requested tools
4) appends tool results back into history
"""

# pyright: reportImportCycles=false

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, cast

from meto.agent.agent import Agent
from meto.agent.context import Context
from meto.agent.exceptions import AgentInterrupted, MaxStepsExceededError
from meto.agent.hooks import (
    post_tool_use,
    pre_tool_use,
)
from meto.agent.hooks.rule_injection import RuleInjectionHook
from meto.agent.orchestrator.client import get_client
from meto.agent.orchestrator.signals import handle_interrupt
from meto.agent.reasoning_log import ReasoningLogger
from meto.agent.system_prompt import build_system_prompt
from meto.agent.tool_registry import registry
from meto.agent.tool_runner import (  # pyright: ignore[reportImportCycles]
    register_tool_handler,
    run_tool,
)
from meto.conf import settings

logger = logging.getLogger("agent")


def run_agent_loop(agent: Agent, prompt: str, context: Context) -> Generator[str, None, None]:
    """Run the agent loop for a single user prompt.

    In interactive mode, this function is called repeatedly and shares
    module state (`history`) so the conversation continues.

    Raises:
        AgentInterrupted: If the user interrupts with Ctrl-C during execution.
        MaxStepsExceededError: If the loop reaches its maximum turn limit.
    """

    if not prompt.strip():
        return

    for tool_name in agent.tool_names:
        registration = registry.catalog.get(tool_name)
        if registration is None:
            continue
        register_tool_handler(registration.name, registration.handler)

    with ReasoningLogger(agent.name) as reasoning_logger:
        reasoning_logger.log_system_prompt(build_system_prompt(agent.prompt))
        reasoning_logger.log_user_input(prompt)
        context.add_message({"role": "user", "content": prompt})

        # Reset rule injection tracking for this new prompt
        RuleInjectionHook.reset_injected_rules()

        with handle_interrupt() as sig:
            for _turn in range(agent.max_turns):
                # Check for interruption at the start of each turn
                if sig.interrupted:
                    reasoning_logger.log_loop_completion("Interrupted by user (Ctrl-C)")
                    raise AgentInterrupted("Agent loop interrupted by user")

                # The OpenAI SDK uses large TypedDict unions for `messages` and `tools`.
                # Our history is intentionally JSON-shaped, so treat these as dynamic.
                system_prompt = build_system_prompt(agent.prompt)
                messages: Any = [
                    {"role": "system", "content": system_prompt},
                    *context.history,
                ]

                resp = get_client().chat.completions.create(
                    model=settings.DEFAULT_MODEL,
                    messages=messages,
                    tools=cast(Any, agent.tools),
                    extra_body={
                        "thinking": {
                            "type": "enabled",  # enable thinking
                            "clear_thinking": False,  # keep reasoning across turns (preserved thinking)
                        }
                    },
                )

                msg = resp.choices[0].message
                assistant_content = msg.content or ""
                tool_calls: list[Any] = list(getattr(msg, "tool_calls", None) or [])

                # Log model reasoning and response
                reasoning_logger.log_model_response(resp, settings.DEFAULT_MODEL)

                # Extract and log reasoning content
                reasoning_content = getattr(msg, "reasoning_content", None) or ""
                if reasoning_content:
                    reasoning_logger.log_reasoning(reasoning_content)

                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": assistant_content,
                }
                if tool_calls:
                    assistant_message["tool_calls"] = [tc.model_dump() for tc in tool_calls]
                if resp.usage:
                    assistant_message["prompt_tokens"] = resp.usage.prompt_tokens
                    assistant_message["completion_tokens"] = resp.usage.completion_tokens
                context.add_message(assistant_message)

                if assistant_content:
                    yield assistant_content

                if not tool_calls:
                    reasoning_logger.log_loop_completion("No more tool calls requested")
                    return

                for tc in tool_calls:
                    tc_any = tc
                    if getattr(tc_any, "type", None) != "function":
                        continue

                    fn = tc_any.function
                    fn_name = getattr(fn, "name", None)
                    if not isinstance(fn_name, str) or not agent.has_tool(fn_name):
                        context.add_message(
                            {
                                "role": "tool",
                                "tool_call_id": tc_any.id,
                                "content": f"Unknown tool: {fn_name}",
                            }
                        )
                        continue

                    try:
                        arguments_raw = getattr(fn, "arguments", None) or "{}"
                        arguments_any = json.loads(arguments_raw)
                    except (TypeError, json.JSONDecodeError) as e:
                        logger.error(f"Failed to parse arguments for {fn_name}: {e}")
                        context.add_message(
                            {
                                "role": "tool",
                                "tool_call_id": tc_any.id,
                                "content": f"Error: Could not parse tool arguments. {e}",
                            }
                        )
                        continue

                    if not isinstance(arguments_any, dict):
                        logger.error(
                            f"Tool arguments for {fn_name} must be a dictionary, got {type(arguments_any).__name__}"
                        )
                        context.add_message(
                            {
                                "role": "tool",
                                "tool_call_id": tc_any.id,
                                "content": f"Error: Tool arguments must be a dictionary, got {type(arguments_any).__name__}",
                            }
                        )
                        continue

                    arguments = cast(dict[str, Any], arguments_any)

                    # Check pre-execution hooks
                    pre_tool_hook_result = pre_tool_use(fn_name, arguments, context)
                    if not pre_tool_hook_result.success:
                        context.add_message(
                            {
                                "role": "tool",
                                "tool_call_id": tc_any.id,
                                "content": pre_tool_hook_result.error
                                or "Action blocked by security policy",
                            }
                        )
                        continue

                    # Inject content if provided by hook (e.g., rules)
                    if pre_tool_hook_result.injected_content:
                        reasoning_logger.log_injected_context(
                            pre_tool_hook_result.injected_content,
                            fn_name,
                        )
                        context.add_message(
                            {
                                "role": "system",
                                "content": pre_tool_hook_result.injected_content,
                            }
                        )
                        # Continue to next turn to let LLM see the context and respond
                        continue

                    # Execute tool (logging happens inside the tool runner)
                    tool_output = run_tool(
                        context,
                        fn_name,
                        arguments,
                        reasoning_logger,
                    )

                    # Check post-execution hooks
                    post_tool_hook_result = post_tool_use(fn_name, arguments, tool_output, context)
                    if not post_tool_hook_result.success:
                        tool_output += (
                            f"\n\n[System] Post-action check failed: {post_tool_hook_result.error}"
                        )

                    context.add_message(
                        {
                            "role": "tool",
                            "tool_call_id": tc_any.id,
                            "content": tool_output,
                        }
                    )

                    if context.pending_tools:
                        existing_tool_names = set(agent.tool_names)
                        for pending_tool in context.pending_tools:
                            function_block = pending_tool.schema.get("function", {})
                            schema_name = function_block.get("name")
                            if not isinstance(schema_name, str):
                                continue

                            if schema_name not in existing_tool_names:
                                agent.tools = (*agent.tools, pending_tool.schema)
                                existing_tool_names.add(schema_name)

                            register_tool_handler(schema_name, pending_tool.handler)

                        context.pending_tools.clear()

        reasoning_logger.log_loop_completion(f"Reached max turns ({agent.max_turns})")
        raise MaxStepsExceededError(f"Exceeded maximum of {agent.max_turns} turns")
