---
name: markdown
description: Markdown formatting and structure guidelines
patterns:
  - "*.md"
---

# Markdown Formatting Guidelines

## Document Structure
- Start with a level 1 heading (`# Title`) for the main document title
- Use level 2 headings (`##`) for major sections
- Use level 3+ headings for subsections
- Maintain consistent heading hierarchy (skip levels)

## Formatting
- Use bold (`**text**`) for emphasis and important terms
- Use italic (`*text*`) for subtle emphasis or book titles
- Use code backticks (`` `code` ``) for inline code references
- Use fenced code blocks (```) for multi-line code snippets

## Links
- Use descriptive link text: `[See the documentation](https://example.com)`
- For internal links, use relative paths: `[See API Reference](api.md)`
- Include URL in full for external links

## Lists
- Use unordered lists (`- item`) for items without specific order
- Use ordered lists (`1. item`) for sequences or steps
- Maintain consistent list marker style within a list
- Indent nested lists by 2 spaces

## Code Blocks
- Specify language for syntax highlighting: ```python
- Include descriptive comments in code examples
- Keep examples concise and focused

## Tables
- Use aligned Markdown tables for tabular data
- Include headers in the first row
- Use `|` for column separators and `|` for row endings

## Best Practices
- Add blank line between paragraphs for readability
- Use horizontal rules (`---`) to separate major sections
- Avoid excessive nesting (more than 3 levels)
- Proofread for spelling and grammar
- Use semantic HTML tags when appropriate (e.g., `<details>`, `<summary>`)
