## ADDED Requirements

### Requirement: `/use` command registration
The system SHALL register a new slash command named `/use`.

#### Scenario: Registering the command
- **WHEN** the CLI application starts
- **THEN** the `/use` command is available in the list of commands

### Requirement: `/use` command invocation with skill name
The system SHALL allow invoking a skill by providing its name as the first argument to `/use`.

#### Scenario: Invoking a skill by name
- **WHEN** the user types `/use context7-docs`
- **THEN** the system attempts to load and execute the `context7-docs` skill

### Requirement: `/use` command with arguments
The system SHALL pass any additional tokens provided after the skill name as arguments to the skill.

#### Scenario: Passing multiple arguments
- **WHEN** the user types `/use my-skill arg1 arg2 "arg with spaces"`
- **THEN** the system invokes `my-skill` with arguments `["arg1", "arg2", "arg with spaces"]`

### Requirement: Error handling for missing skill
The system SHALL inform the user if the specified skill does not exist.

#### Scenario: Invoking a non-existent skill
- **WHEN** the user types `/use non-existent-skill`
- **THEN** the system displays an error message: "Skill 'non-existent-skill' not found."
