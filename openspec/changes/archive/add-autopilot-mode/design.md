## Context

Meto currently relies on the user to manually sequence complex tasks. While subagents exist via `run_task`, they operate as isolated "one-offs" without a formal mechanism to pass state or discoveries between sequential sessions. This leads to context bloat in the main session or lost information in subagent sessions. Autopilot Mode introduces a structured Orchestrator to bridge this gap.

## Goals / Non-Goals

**Goals:**
- Enable autonomous execution of multi-step roadmaps.
- Maintain persistent state to survive crashes or restarts.
- Ensure fresh context for every sub-task to avoid "context poisoning".
- Provide a standardized handover protocol between sub-tasks.

**Non-Goals:**
- Completely removing the human from the loop (HITL is still required for failures).
- Implementing a generic agentic framework (focused specifically on Meto's coding tasks).
- Automatic self-modification of Meto's core source code.

## Decisions

### 1. Persistent State via JSON
**Decision:** Use a local `.autopilot_state.json` file to store the roadmap and task statuses.
**Rationale:** It is lightweight, human-readable, and easily integrated into Meto's existing file-based configuration patterns.
**Alternatives Considered:** SQLite (overkill for simple task tracking), Memory-only (unacceptable for long-running autonomous tasks).

### 2. Fresh-Context Subagents (The Executor)
**Decision:** Every sub-task starts a fresh `run_agent_loop` with a cleared history.
**Rationale:** Prevents "context drift" where the model loses focus due to old tool outputs or irrelevant conversation history.
**Alternatives Considered:** Summarizing old history (computationally expensive and often loses critical details).

### 3. Leveraging Existing `planner` Agent
**Decision:** Use the existing `planner` agent for the initial roadmap generation and re-planning.
**Rationale:** Reuses existing domain expertise and avoids logic duplication.
**Alternatives Considered:** Creating a new `orchestrator` specific agent.

### 4. Regex-based Handover Extraction
**Decision:** Use a structured Markdown template and regex to extract handover data from subagent responses.
**Rationale:** Simple to implement and debug.
**Alternatives Considered:** Forcing subagents to use a specialized `generate_handover` tool (more rigid, but might be safer in the future).

## Risks / Trade-offs

- **[Risk] Loop Divergence / Infinite Loops** → **Mitigation:** Implement a hard limit of 30 turns per autopilot session and a maximum of 3 retries per sub-task.
- **[Risk] Context Loss in Handover** → **Mitigation:** The Handover Prompt template includes a mandatory "Critical Discoveries" section to ensure non-obvious knowledge is preserved.
- **[Risk] State Corruption** → **Mitigation:** Implement atomic writes for the `.autopilot_state.json` file.
- **[Risk] Cost Overruns** → **Mitigation:** Introduce an optional token/cost budget circuit breaker.
