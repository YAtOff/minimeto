## 1. Skill Engine Enhancements

- [ ] 1.1 Update `SkillLoader` to parse new frontmatter fields: `allowed-tools`, `context`, `agent`, and `model`.
- [ ] 1.2 Implement a `SkillExpander` class or utility function for handling variable and command expansion.
- [ ] 1.3 Add support for `$ARGUMENTS` expansion (joins all args with spaces).
- [ ] 1.4 Add support for `$ARGUMENTS[N]` expansion for indexed access.
- [ ] 1.5 Add support for `$(cmd)` expansion by executing shell commands and capturing stdout.

## 2. Slash Command Implementation

- [ ] 2.1 Register the `/use` command in `src/meto/agent/command.py`.
- [ ] 2.2 Implement the `/use` handler logic: parse tokens, load skill, expand body.
- [ ] 2.3 Integrate error handling for missing skills or expansion failures.

## 3. Execution Context & Constraints

- [ ] 3.1 Update `AgentLoop` and `Agent` factory to accept an optional `tool_filter` list.
- [ ] 3.2 Ensure the agent only sees the filtered tools when `tool_filter` is provided.
- [ ] 3.3 Implement the `context: fork` logic in the `/use` command (spawn a sub-agent or new loop).
- [ ] 3.4 Wire up the `agent` and `model` frontmatter overrides to the forked agent loop.

## 4. Testing & Verification

- [ ] 4.1 Create unit tests for variable and command expansion in skill bodies.
- [ ] 4.2 Create integration tests for the `/use` command with various argument combinations.
- [ ] 4.3 Verify `allowed-tools` correctly restricts tool access in a live session.
- [ ] 4.4 Verify `context: fork` correctly isolates history when requested.
