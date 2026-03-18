## Why

Meto currently operates primarily as a reactive tool for individual commands. Autopilot Mode is needed to enable the agent to execute complex, multi-step coding tasks autonomously. This solves the problem of "context poisoning" and "context drift" that occurs in long-running sessions by using a recursive loop with fresh context for each sub-task, ensuring architectural consistency and efficiency.

## What Changes

- **Planner-Executor Model**: Separation of high-level strategy (Planner/Orchestrator) from low-level execution (Executor/Subagent).
- **Recursive Control Loop**: A formal cycle for task initialization, execution, verification, and handover.
- **Autopilot State Persistence**: Implementation of a persistent state file (`.autopilot_state.json`) to allow sessions to resume after interruptions.
- **Handover Protocol**: Standardized template for passing critical discoveries and next steps between subagent sessions.
- **Context Management**: Logic for "Summarize-and-Prune" of terminal outputs and context zoning (Static, Persistent, Transient).
- **Technical Safeguards**: Circuit breakers for token/step budgets and self-correction limits.

## Capabilities

### New Capabilities
- `autopilot-orchestrator`: Manages the global roadmap, state persistence, and recursive loop orchestration.
- `autopilot-executor`: Handles individual sub-task execution with fresh context and standardized handover generation.
- `autopilot-state-management`: Provides a robust, persistent tracking system for task status and progress.

### Modified Capabilities
(None)

## Impact

- **Core Agent Loop**: `src/meto/agent/agent_loop.py` will need integration points for the autopilot loop.
- **Task Management**: `src/meto/agent/todo.py` or new roadmap modules will be impacted.
- **CLI/Commands**: New slash commands and CLI flags for autopilot mode.
- **Project Structure**: Introduction of `.autopilot_state.json` and new state-tracking logic.
