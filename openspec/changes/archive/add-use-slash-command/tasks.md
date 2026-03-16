## 1. Skill Engine Enhancements

- [x] 1.1 Update `SkillLoader` to parse new frontmatter fields: `allowed-tools`, `context`, `agent`, and `model`.
- [x] 1.2 Implement a `SkillExpander` class or utility function for handling variable and command expansion.
- [x] 1.3 Add support for `$ARGUMENTS` expansion (joins all args with spaces).
- [x] 1.4 Add support for `$ARGUMENTS[N]` expansion for indexed access.
- [x] 1.5 Add support for `$(cmd)` expansion by executing shell commands and capturing stdout.

## 2. Slash Command Implementation

- [x] 2.1 Register the `/use` command in `src/meto/agent/command.py`.
- [x] 2.2 Implement the `/use` handler logic: parse tokens, load skill, expand body.
- [x] 2.3 Integrate error handling for missing skills or expansion failures.

## 3. Execution Context & Constraints

- [x] 3.1 Update `AgentLoop` and `Agent` factory to accept an optional `tool_filter` list.
- [x] 3.2 Ensure the agent only sees the filtered tools when `tool_filter` is provided.
- [x] 3.3 Implement the `context: fork` logic in the `/use` command (spawn a sub-agent or new loop).
- [x] 3.4 Wire up the `agent` and `model` frontmatter overrides to the forked agent loop.

## 4. Testing & Verification

- [x] 4.1 Create unit tests for variable and command expansion in skill bodies.
- [x] 4.2 Create integration tests for the `/use` command with various argument combinations.
- [x] 4.3 Verify `allowed-tools` correctly restricts tool access in a live session.
- [x] 4.4 Verify `context: fork` correctly isolates history when requested.
