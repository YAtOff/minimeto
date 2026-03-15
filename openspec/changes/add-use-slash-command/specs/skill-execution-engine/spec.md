## ADDED Requirements

### Requirement: `$ARGUMENTS` variable expansion
The system SHALL expand the `$ARGUMENTS` variable in the skill body with all arguments passed to the skill.

#### Scenario: Full argument expansion
- **WHEN** a skill is invoked with `arg1` and `arg2`
- **THEN** `$ARGUMENTS` is replaced with `"arg1 arg2"` (or equivalent space-separated string)

### Requirement: `$ARGUMENTS[N]` indexed expansion
The system SHALL expand `$ARGUMENTS[N]` where `N` is an integer index (starting from 0) representing the N-th argument.

#### Scenario: Expanding a specific argument
- **WHEN** a skill is invoked with arguments `["first", "second", "third"]`
- **THEN** `$ARGUMENTS[0]` is replaced with `"first"`, `$ARGUMENTS[1]` with `"second"`, etc.

### Requirement: `$(cmd)` command execution and injection
The system SHALL execute shell commands enclosed in `$(...)` and inject their stdout output into the skill's content at runtime.

#### Scenario: Dynamic context injection
- **WHEN** the skill body contains `$(date +%Y)`
- **THEN** the system executes the command and replaces the expression with its output (e.g., `2026`)

### Requirement: Skill frontmatter: `allowed-tools`
The system SHALL restrict the agent loop to only the tools listed in the `allowed-tools` field of the skill's frontmatter.

#### Scenario: Restricted tool set
- **WHEN** a skill's frontmatter contains `allowed-tools: ["shell", "read_file"]`
- **THEN** the agent loop for that skill only allows those two tools

### Requirement: Skill frontmatter: `context: fork`
The system SHALL run the agent loop for the skill in a forked context when `context: fork` is specified in the frontmatter.

#### Scenario: Forking context
- **WHEN** a skill has `context: fork`
- **THEN** a new agent loop is started with its own session/history, potentially inheriting from the current one but isolated

### Requirement: Skill frontmatter: `agent` override
The system SHALL use the specified agent for the agent loop when the `agent` field is provided in the frontmatter.

#### Scenario: Overriding the agent
- **WHEN** a skill has `agent: planner`
- **THEN** the system uses the `planner` agent configuration for the execution

### Requirement: Skill frontmatter: `model` override
The system SHALL use the specified LLM model when the `model` field is provided in the frontmatter.

#### Scenario: Overriding the model
- **WHEN** a skill has `model: gpt-4o`
- **THEN** the agent loop uses `gpt-4o` for its LLM calls
