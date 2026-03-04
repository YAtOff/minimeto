---
name: general
description: General coding guidelines for all file types
patterns:
  - "*"
---

# General Coding Guidelines

## Code Quality
- Write clear, readable code that is self-documenting
- Use meaningful variable and function names
- Avoid abbreviations unless widely understood
- Keep functions focused on a single responsibility

## Error Handling
- Always handle potential errors gracefully
- Provide meaningful error messages
- Log errors with appropriate context
- Fail fast when encountering invalid state

## Security
- Never hardcode credentials, API keys, or secrets
- Use environment variables for configuration
- Validate and sanitize user input
- Follow the principle of least privilege

## Testing
- Write tests for critical functionality
- Test edge cases and error conditions
- Use descriptive test names
- Keep tests independent and isolated

## Documentation
- Document non-obvious code logic
- Keep comments up-to-date with code changes
- Prefer self-documenting code over excessive comments
- Include examples in documentation

## Performance
- Avoid premature optimization
- Profile before optimizing
- Consider time and space complexity
- Use appropriate data structures

## Version Control
- Write clear, descriptive commit messages
- Make small, focused commits
- Review changes before committing
- Use .gitignore appropriately

## Collaboration
- Follow the project's established conventions
- Request code reviews for significant changes
- Communicate breaking changes to the team
- Document dependencies and requirements
