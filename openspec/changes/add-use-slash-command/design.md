## Context

The current `meto` architecture supports skills as static context injected into the agent loop. There is no direct way to pass parameters to skills or restrict the tools available to them during execution. This design introduces the `/use` command and enhances the skill processing engine to support dynamic parameterization and controlled execution environments.

## Goals / Non-Goals

**Goals:**
- Provide a direct CLI entry point for skills via `/use`.
- Support positional arguments for skills.
- Allow dynamic runtime context injection via shell command execution within skills.
- Enable skill-specific execution constraints (tools, agent, model).
- Support forking for clean execution context.

**Non-Goals:**
- Complex control flow within skills (e.g., if/else logic).
- Interactive argument prompting (arguments must be provided on command line).
- Skill-to-skill direct calling (can be achieved via `/use` in body if expanded).

## Decisions

- **Command Registration**: Register `/use` in `src/meto/agent/command.py`. It will leverage `SkillLoader` to find and read skill files.
- **Dynamic Variable Expansion**:
    - **Implementation**: A new utility function or method in `SkillLoader` to perform regex-based substitution.
    - **Order**: `$(cmd)` expansion should happen before `$ARGUMENTS` expansion to allow shell commands to potentially use arguments.
- **Forked Context (Sub-Agents)**:
    - **Mechanism**: Use the `run_task` logic or similar abstraction. When `context: fork` is specified, the `/use` command will create a new session/agent loop.
    - **Inheritance**: The forked context will NOT inherit the full parent history by default, providing a clean slate for the skill's specific task.
- **Tool Filtering**:
    - **Implementation**: The `AgentLoop` or `Agent` factory should accept a `tool_filter` list. When provided, only tools present in the filter will be available to the LLM.
- **Runtime Command Injection (`$(cmd)`)**:
    - **Mechanism**: Use `subprocess.check_output(cmd, shell=True)` (or equivalent safe wrapper). Output is captured, UTF-8 decoded, and stripped.

## Risks / Trade-offs

- **Security Risk (`$(cmd)`)**: Executing arbitrary commands from skill files is dangerous.
    - **Mitigation**: This capability is intended for trusted local skills. The user is already giving the agent `shell` tool access in many cases. We will ensure this is clearly documented.
- **Complexity Trade-off**: Forking contexts adds overhead.
    - **Mitigation**: We will only fork if explicitly requested in frontmatter.
- **Conflict with existing syntax**: `$` and `(` are common characters.
    - **Mitigation**: Use specific regex patterns like `\$ARGUMENTS\[(\d+)\]` and `\$\((.*?)\)` to minimize false positives.
