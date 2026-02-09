---
name: git-commit
description: Create well-formed git commits following Conventional Commits specification
---

# Git Commit

You are an expert at creating clear, actionable git commits that communicate intent and enable efficient codebase navigation.

## Core Principles

- **Conventional Commits format**: Structured commits enable automated changelogs and semantic versioning
- **Imperative mood**: "Add feature" not "Added feature" or "Adding feature"
- **Concise subject line**: Max 50 characters, explain WHAT and WHY (not HOW)
- **Separate subject from body**: Blank line between, wrap body at 72 characters
- **Explain WHAT and WHY**: How is visible in the diff; focus on intent

**Announce at start:** "I'm using the git-commit skill to create a commit."

## Conventional Commits Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD configuration changes
- `chore`: Other changes that don't modify src or test files

**Examples**:
```
feat(auth): add OAuth2 login support

Implement OAuth2 flow with Google and GitHub providers.
Users can now link multiple accounts to their profile.

Fixes #123
```

```
fix(api): handle null response from payment gateway

Previously, null responses would crash the payment worker.
Now returns error response to client for retry.

Closes #456
```

```
refactor(utils): extract date formatting to shared module

Reduces duplication across 5 files. No behavior change.
```

## Commit Workflow

### 1. Gather Context

```bash
git status                    # See changed files
git diff HEAD                 # See staged + unstaged changes
git branch --show-current     # Current branch
git log --oneline -10         # Recent commits for style consistency
```

### 2. Analyze Changes

- **What changed?** Scan diff for modified functions, added features, bug fixes
- **Why change?** Identify intent from affected code
- **Scope?** Which module/subsystem is affected?
- **Type?** feat/fix/docs/refactor/etc.

### 3. Generate Candidates

Draft 3 commit messages following Conventional Commits:
- Candidate 1: Focus on primary intent
- Candidate 2: Alternative scope/type emphasis
- Candidate 3: Different detail level

### 4. Select and Explain

Choose best candidate. Explain reasoning:
- Why this type/scope?
- Why this level of detail?
- How it fits recent commit style?

### 5. Stage and Commit

```bash
git add <files>               # Stage specific files (not git add .)
git commit -m "<message>"     # Commit with selected message
```

## Common Mistakes

**Vague subjects**
- Bad: "Update code" / "Fix stuff" / "Changes"
- Good: "feat: add user profile page" / "fix: handle null pointer"

**Non-imperative mood**
- Bad: "Added feature" / "Adding feature" / "Fixes bug"
- Good: "Add feature" / "Fix bug"

**Subject too long**
- Bad: "feat(auth): implement OAuth2 login flow with Google provider and token refresh"
- Good: "feat(auth): add OAuth2 login with Google"

**Including HOW in subject**
- Bad: "fix: change loop to use map function"
- Good: "fix: simplify data transformation"

**Over-generic type**
- Bad: `chore:` for a user-facing feature
- Good: `feat:` for new features, even small ones

## Examples

### Feature Addition
```
feat: add dark mode toggle

Add theme switcher in settings. Persists choice in localStorage.
Follows system preference by default.
```

### Bug Fix
```
fix: prevent duplicate form submissions

Disable submit button after first click. Fixes issue where
users could create duplicate orders by double-clicking.

Fixes #789
```

### Refactor
```
refactor(auth): extract session logic to dedicated module

Moves session management from user.py to new session.py.
Improves testability and reduces coupling. No behavior change.
```

### Documentation
```
docs: clarify API authentication flow

Add diagrams showing token refresh flow. Update examples
to use new auth headers format.
```

## Red Flags

**Never**:
- Use `git add .` or `git add -A` (stage specific files)
- Commit generated files (build artifacts, dependencies, cache)
- Include file content in commit message (diff shows this)
- Use generic messages like "update" or "fix"
- Add co-authorship footers for automated tools

**Always**:
- Use imperative mood in subject
- Explain WHAT and WHY (not HOW)
- Keep subject under 50 characters
- Reference issue numbers in footer when applicable
- Stage files deliberately (avoid unintended inclusions)
