## 1. State & Infrastructure

- [x] 1.1 Create `src/meto/agent/autopilot/` package and initialize it.
- [x] 1.2 Implement `AutopilotState` for persistent task management (reading/writing `.autopilot_state.json`).
- [x] 1.3 Define Pydantic models for `AutopilotTask` (Pending, Running, Completed, Failed) and `AutopilotSession`.

## 2. Loop & Orchestration

- [x] 2.1 Implement the core `run_autopilot_loop` in `src/meto/agent/autopilot/loop.py`.
- [x] 2.2 Enhance the existing `planner` agent instructions to better support recursive autopilot roadmaps.
- [x] 2.3 Implement the task selection logic to pick the next pending task from the roadmap.

## 3. Handover & Context

- [x] 3.1 Implement the Handover Prompt template in `src/meto/agent/system_prompt.py`.
- [x] 3.2 Create a regex-based parser to extract `### 🎯 Task Completed` blocks from LLM assistant responses.
- [x] 3.3 Implement the "Context Capsule" assembly logic to pass state between `run_agent_loop` calls.

## 4. Safeguards & Git Integration

- [x] 4.1 Implement automatic, atomic Git commits after each successful sub-task completion.
- [x] 4.2 Implement "Circuit Breakers": hard turn limits (30 turns) and max retries per task (3 attempts).
- [x] 4.3 Implement "Summarize-and-Prune" logic to compress large tool outputs before they enter the transient context.

## 5. CLI & UX Integration

- [x] 5.1 Add the `/autopilot` slash command to `src/meto/agent/command.py`.
- [x] 5.2 Update `src/meto/cli.py` to support the `--autopilot` command-line flag.
- [x] 5.3 Integrate `rich.progress` or `rich.panel` for real-time visualization of the autopilot roadmap status.
