## ADDED Requirements

### Requirement: Recursive Task Execution Loop
The system SHALL implement a recursive loop that iterates through the global roadmap, spawning a new executor for each pending task until the goal is reached or a circuit breaker is triggered.

#### Scenario: Continuous execution of sequential tasks
- **WHEN** the roadmap contains multiple pending tasks
- **THEN** the orchestrator SHALL execute them one by one, passing the handover from the previous task to the next.

### Requirement: Goal Decomposition
The orchestrator SHALL use the existing `planner` agent to decompose the user's high-level goal into a discrete roadmap of sub-tasks.

#### Scenario: Initial goal decomposition
- **WHEN** a user starts an autopilot session with a complex goal
- **THEN** the orchestrator SHALL call the planner agent to generate a structured list of tasks.

### Requirement: Task Status Monitoring
The orchestrator SHALL track the real-time status (Pending, Running, Completed, Failed) of every task in the roadmap.

#### Scenario: Tracking task completion
- **WHEN** a subagent finishes a task successfully
- **THEN** the orchestrator SHALL mark that task as 'Completed' in the global state.

### Requirement: Re-planning on Failure
The orchestrator SHALL detect sub-task failures and trigger a re-planning phase to adjust the roadmap or retry the task.

#### Scenario: Sub-task failure triggers re-planning
- **WHEN** a subagent reports a blocking error
- **THEN** the orchestrator SHALL invoke the planner to provide an updated roadmap or alternative path.
