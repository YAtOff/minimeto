from __future__ import annotations

import logging

from meto.agent.exceptions import LLMError
from meto.agent.orchestrator.client import get_client
from meto.conf import settings

logger = logging.getLogger(__name__)


def summarize_tool_output(tool_name: str, output: str, max_chars: int = 2000) -> str:
    """Summarize tool output using an LLM to prune the context.

    Args:
        tool_name: The name of the tool that produced the output.
        output: The raw tool output to summarize.
        max_chars: The maximum length for the fallback truncation if summarization fails.
            Note: The LLM is prompted using settings.MAX_TOOL_OUTPUT_CHARS as a target
            size for the summary, while max_chars is used locally for immediate truncation
            on error.

    Returns:
        A summarized or truncated version of the output.
    """
    if output.startswith("__METO_IMAGE__:") or len(output) <= max_chars:
        return output

    logger.info("Summarizing large output from tool '%s' (%d chars)", tool_name, len(output))

    prompt = (
        f"The following is a large output from the tool '{tool_name}'. "
        "Please provide a concise summary that preserves all critical details "
        "needed for a software engineer to continue their work. "
        "Include error messages, key paths, or important data points if present.\n\n"
        f"OUTPUT:\n{output[: settings.MAX_TOOL_OUTPUT_CHARS]}"
    )

    try:
        resp = get_client().chat.completions.create(
            model=settings.COMPACT_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes technical tool outputs.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        summary = resp.choices[0].message.content or "(Failed to generate summary)"
        return f"[Output summarized from {len(output)} chars]\n\nSUMMARY:\n{summary}"
    except (LLMError, Exception) as e:
        logger.error(
            f"Unexpected error summarizing output from tool '{tool_name}': {e}",
            exc_info=True,
        )
        # Fallback to simple truncation
        return (
            f"[Output truncated from {len(output)} chars due to unexpected error]\n\n"
            f"{output[:max_chars]}..."
        )
