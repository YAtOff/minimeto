## Why

Currently, skills are loaded into the agent's context to provide specialized knowledge, but there is no direct way to invoke a skill with arguments via a slash command. This change introduces the `/use` command to provide a more interactive way to leverage skills, while also significantly expanding the capabilities of skills themselves through controlled tool access, context forking, and dynamic context injection.

## What Changes

- **New `/use` Slash Command**: Introduces `/use <skill-name> [args...]` to invoke a skill directly.
- **Skill Frontmatter Enhancements**:
    - `allowed-tools`: Restrict the tools available during the skill's execution.
    - `context: fork`: Option to run the skill in a separate agent loop (forked context).
    - `agent`: Specify a custom agent name to use when `context: fork` is enabled.
    - `model`: Specify a custom LLM model for the skill's execution.
- **Dynamic Skill Body Expansion**:
    - `$ARGUMENTS` and `$ARGUMENTS[N]` variables for argument passing.
    - `$(cmd)` syntax to execute shell commands and inject their output into the skill context at runtime.

## Capabilities

### New Capabilities
- `use-slash-command`: The command handler for `/use` and its integration with the terminal.
- `skill-execution-engine`: Enhanced skill loading, frontmatter parsing, and runtime variable/command expansion.

### Modified Capabilities
- None (as `openspec/specs/` is empty).

## Impact

- `src/meto/agent/command.py`: New `/use` command registration.
- `src/meto/agent/loaders/skill_loader.py`: Updated to parse new frontmatter fields and handle variable expansion.
- `src/meto/agent/agent_loop.py`: Potential changes to support forked contexts and restricted toolsets during skill execution.
- `src/meto/agent/tools/skill_tools.py`: Updates to the `load_skill` tool if its behavior is shared with the new command.
