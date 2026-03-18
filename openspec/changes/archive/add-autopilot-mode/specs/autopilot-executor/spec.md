## ADDED Requirements

### Requirement: Isolated Context Execution
Each sub-task SHALL be executed in a fresh subagent instance with a cleared conversation history to prevent context bloat and "poisoning".

#### Scenario: Starting a sub-task with clean history
- **WHEN** a new sub-task is initiated
- **THEN** the executor SHALL start with a fresh history containing only the system prompt and the current Context Capsule.

### Requirement: Context Capsule Initialization
The executor SHALL be initialized with a "Context Capsule" containing the global goal, the specific sub-task instructions, and relevant discoveries from previous steps.

#### Scenario: Receiving handover data
- **WHEN** a sub-task starts after a previous one
- **THEN** the executor SHALL include the 'Critical Discoveries' from the previous task's handover in its initial context.

### Requirement: Handover Generation
At the conclusion of every session, the subagent SHALL generate a standardized Handover Prompt including achieved results, changes made, and critical discoveries.

#### Scenario: Generating a successful handover
- **WHEN** a subagent completes its assigned task
- **THEN** it SHALL output a markdown block following the 'Handover Prompt' template.

### Requirement: Summarize-and-Prune
The executor SHALL implement logic to summarize large terminal outputs or long history segments before they are passed back to the orchestrator or next subagent.

#### Scenario: Handling large tool outputs
- **WHEN** a shell command returns output exceeding the token threshold
- **THEN** the system SHALL summarize the output before adding it to the transient context.
