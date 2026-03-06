---
name: "context7-docs"
description: "Query up-to-date documentation and code examples for any programming library or framework using Context7. Use this skill when you need current API docs, usage examples, or guidance for a specific library version."
---

# mcp CLI

## Tool Commands

### resolve-library-id

Resolves a package/product name to a Context7-compatible library ID and returns matching libraries.

You MUST call this function before 'Query Documentation' tool to obtain a valid Context7-compatible library ID UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query.

Each result includes:
- Library ID: Context7-compatible identifier (format: /org/project)
- Name: Library or package name
- Description: Short summary
- Code Snippets: Number of available code examples
- Source Reputation: Authority indicator (High, Medium, Low, or Unknown)
- Benchmark Score: Quality indicator (100 is the highest score)
- Versions: List of versions if available. Use one of those versions if the user provides a version in their query. The format of the version is /org/project/version.

For best results, select libraries based on name match, source reputation, snippet coverage, benchmark score, and relevance to your use case.

Selection Process:
1. Analyze the query to understand what library/package the user is looking for
2. Return the most relevant match based on:
- Name similarity to the query (exact matches prioritized)
- Description relevance to the query's intent
- Documentation coverage (prioritize libraries with higher Code Snippet counts)
- Source reputation (consider libraries with High or Medium reputation more authoritative)
- Benchmark Score: Quality indicator (100 is the highest score)

Response Format:
- Return the selected library ID in a clearly marked section
- Provide a brief explanation for why this library was chosen
- If multiple good matches exist, acknowledge this but proceed with the most relevant one
- If no good matches exist, clearly state this and suggest query refinements

For ambiguous queries, request clarification before proceeding with a best-guess match.

IMPORTANT: Do not call this tool more than 3 times per question. If you cannot find what you need after 3 calls, use the best result you have.

```bash
uv run --with fastmcp python scripts/ctx7cli.py call-tool resolve-library-id --query <value> --library-name <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--query` | string | yes | The question or task you need help with. This is used to rank library results by relevance to what the user is trying to accomplish. The query is sent to the Context7 API for processing. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query. |
| `--library-name` | string | yes | Library name to search for and retrieve a Context7-compatible library ID. |

### query-docs

Retrieves and queries up-to-date documentation and code examples from Context7 for any programming library or framework.

You must call 'Resolve Context7 Library ID' tool first to obtain the exact Context7-compatible library ID required to use this tool, UNLESS the user explicitly provides a library ID in the format '/org/project' or '/org/project/version' in their query.

IMPORTANT: Do not call this tool more than 3 times per question. If you cannot find what you need after 3 calls, use the best information you have.

```bash
uv run --with fastmcp python scripts/ctx7cli.py call-tool query-docs --library-id <value> --query <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--library-id` | string | yes | Exact Context7-compatible library ID (e.g., '/mongodb/docs', '/vercel/next.js', '/supabase/supabase', '/vercel/next.js/v14.3.0-canary.87') retrieved from 'resolve-library-id' or directly from user query in the format '/org/project' or '/org/project/version'. |
| `--query` | string | yes | The question or task you need help with. Be specific and include relevant details. Good: 'How to set up authentication with JWT in Express.js' or 'React useEffect cleanup function examples'. Bad: 'auth' or 'hooks'. The query is sent to the Context7 API for processing. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query. |

## Utility Commands

```bash
uv run --with fastmcp python scripts/ctx7cli.py list-tools
uv run --with fastmcp python scripts/ctx7cli.py list-resources
uv run --with fastmcp python scripts/ctx7cli.py read-resource <uri>
uv run --with fastmcp python scripts/ctx7cli.py list-prompts
uv run --with fastmcp python scripts/ctx7cli.py get-prompt <name> [key=value ...]
```
