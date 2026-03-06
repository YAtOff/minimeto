---
name: review-pr
description: Comprehensive PR review using specialized agents
---

# PR Review

You are an expert code reviewer. Run comprehensive pull request reviews using multiple specialized agents, each focusing on different aspects of code quality.

**Announce at start:** "I'm using the review-pr skill to review this PR."

## Core Principles

- **Sequential reviews**: Run agents one at a time for clarity
- **Focus on changes**: Review git diff, not entire codebase
- **Actionable feedback**: Provide file:line references for all issues
- **Prioritize**: Critical > Important > Suggestions

## Review Workflow

### 0. Setup Agents

**Before launching any review agent, you must load it first:**

```
Use load_agent tool for each agent you plan to use:
- load_agent("code-reviewer")
- load_agent("silent-failure-hunter")
- load_agent("comment-analyzer")
- load_agent("pr-test-analyzer")
- load_agent("type-design-analyzer")
- load_agent("code-simplifier")

After loading, use run_task to execute:
- run_task(prompt="...", agent_name="code-reviewer", description="...")
```

### 1. Determine Scope

```bash
git status                    # Changed files
git diff --name-only          # Modified files list
gh pr view 2>/dev/null || true  # Check if PR exists
```

Parse user arguments:
- No args or `all`: Run all applicable reviews
- Specific args: Run only requested aspects

### 2. Available Review Aspects

| Aspect | Agent Name | When to Use |
|--------|-----------|-------------|
| `comments` | comment-analyzer | Comments/docs added |
| `tests` | pr-test-analyzer | Test files changed |
| `errors` | silent-failure-hunter | Error handling changed |
| `types` | type-design-analyzer | Types added/modified |
| `code` | code-reviewer | Always applicable |
| `simplify` | code-simplifier | After passing review |
| `all` | *all applicable* | Default |

**Important**: First use `load_agent(agent_name)` then `run_task(agent_name=..., prompt=...)`

### 3. Determine Applicable Reviews

Based on changes:
- **Always**: `code-reviewer` (general quality)
- **Test files changed**: `pr-test-analyzer`
- **Comments/docs added**: `comment-analyzer`
- **Error handling changed**: `silent-failure-hunter`
- **Types added/modified**: `type-design-analyzer`
- **After passing review**: `code-simplifier` (polish)

### 4. Launch Agents Sequentially

**For each agent you need to run:**

1. **Load the agent first:**
   ```
   load_agent("code-reviewer")
   ```
   This loads the agent configuration and makes it available.

2. **Then execute the agent:**
   ```
   run_task(
     agent_name="code-reviewer",
     prompt="Review the last commit (git diff HEAD~1..HEAD)",
     description="Code review of recent changes"
   )
   ```

**Important**: Run agents ONE AT A TIME. Wait for each to complete before loading and launching the next.

### 5. Aggregate Results

Organize findings by priority:

```markdown
# PR Review Summary

## Critical Issues (X found)
- [agent-name]: Issue description [file:line]

## Important Issues (X found)
- [agent-name]: Issue description [file:line]

## Suggestions (X found)
- [agent-name]: Suggestion [file:line]

## Strengths
- What's well-done

## Recommended Action
1. Fix critical issues first
2. Address important issues
3. Consider suggestions
4. Re-run review after fixes
```

## Agent Reference

**comment-analyzer**: Verifies comment accuracy vs code, identifies comment rot, checks documentation completeness

**pr-test-analyzer**: Reviews behavioral test coverage, identifies critical gaps, evaluates test quality

**silent-failure-hunter**: Finds silent failures, reviews catch blocks, checks error logging

**type-design-analyzer**: Analyzes type encapsulation, reviews invariant expression, rates type design quality

**code-reviewer**: Checks project documentation compliance, detects bugs and issues, reviews general code quality

**code-simplifier**: Simplifies complex code, improves clarity, applies project standards, preserves functionality

## Usage Patterns

**Before committing:**
```
load_agent("code-reviewer")
load_agent("silent-failure-hunter")

run_task(agent_name="code-reviewer", prompt="Review git diff", description="Code review")
# Wait for completion...
run_task(agent_name="silent-failure-hunter", prompt="Review error handling in git diff", description="Error handling review")
```

**Before creating PR:**
```
# Determine applicable reviews first
git diff --name-only

# Load all needed agents
load_agent("code-reviewer")
load_agent("silent-failure-hunter")
load_agent("pr-test-analyzer")

# Run sequentially, waiting for each to complete
run_task(agent_name="code-reviewer", prompt="Review the PR changes", description="Code review")
# Wait for completion...
run_task(agent_name="silent-failure-hunter", prompt="Review error handling", description="Error handling review")
# Wait for completion...
run_task(agent_name="pr-test-analyzer", prompt="Review test coverage", description="Test coverage review")
```

**Targeted review:**
```
load_agent("pr-test-analyzer")
load_agent("silent-failure-hunter")

run_task(agent_name="pr-test-analyzer", prompt="Review test coverage for PR", description="Test review")
# Wait for completion...
run_task(agent_name="silent-failure-hunter", prompt="Review error handling", description="Error review")
```
