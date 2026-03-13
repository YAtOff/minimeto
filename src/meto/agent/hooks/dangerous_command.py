"""Hook to detect and block dangerous shell commands using LLM analysis.

This hook uses an LLM to analyze shell commands before execution and blocks
those deemed dangerous (destructive, irreversible, security risks).

Unlike permission hooks, this hook is NOT bypassed by yolo mode - it always
runs when enabled to protect against dangerous operations.
"""

from __future__ import annotations

import json
from typing import override

from meto.agent.hooks.base import ErrorResult, HookResult, PreToolUseHook, SuccessResult
from meto.agent.orchestrator.client import get_client
from meto.conf import settings

# Prompt for LLM analysis - requests structured JSON response
DANGEROUS_COMMAND_PROMPT = """Analyze this shell command and determine if it is dangerous.

A command is considered dangerous if it:
- Destroys or deletes files/directories (rm, del, rmdir, format, shred, etc.)
- Modifies system files or configurations (/etc/, ~/.ssh/, ~/.gnupg/, etc.)
- Downloads and executes remote code (curl | bash, wget | sh, etc.)
- Changes file permissions recursively on critical directories
- Encrypts files (ransomware-like behavior)
- Fork bombs or resource exhaustion attacks
- Modifies PATH or environment variables maliciously
- Runs with elevated privileges unnecessarily (sudo, su) for risky operations
- Uses obfuscation techniques (base64 -d | sh, xxd -r -p | sh, etc.)
- Accesses credentials, secrets, or sensitive data (.env, credentials, keys)
- Exfiltrates data to external servers

Command: {command}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"dangerous": true/false, "reason": "brief explanation if dangerous", "category": "category if dangerous"}}

Categories: filesystem_destruction, system_modification, remote_code_execution,
privilege_escalation, data_exfiltration, credential_access, obfuscated_code,
resource_abuse, network_attack"""


class DangerousCommandHook(PreToolUseHook):
    """Check for dangerous shell commands using LLM analysis.

    This hook blocks dangerous commands even when permissions are disabled (yolo mode).
    It uses a separate enable flag (DANGEROUS_COMMAND_ENABLED) for explicit control.
    """

    matched_tools: list[str] | None = ["shell"]

    @override
    def run(self) -> HookResult:
        """Analyze the shell command with LLM and block if dangerous."""
        # Check if hook is enabled (separate from PERMISSIONS_ENABLED)
        if not getattr(settings, "DANGEROUS_COMMAND_ENABLED", True):
            return SuccessResult()

        command = self.arguments.get("command", "")
        if not command:
            return SuccessResult()

        # Check command length - skip analysis for very long commands
        max_length = getattr(settings, "DANGEROUS_COMMAND_MAX_LENGTH", 10000)
        if len(command) > max_length:
            fallback = getattr(settings, "DANGEROUS_COMMAND_FALLBACK", "block")
            if fallback == "block":
                return ErrorResult(
                    error=f"Command exceeds maximum length ({max_length} chars) and fallback is 'block'"
                )
            return SuccessResult()

        # Check allowlist patterns
        allowlist = getattr(settings, "DANGEROUS_COMMAND_ALLOWLIST", [])
        for pattern in allowlist:
            if pattern in command:
                return SuccessResult()

        # Analyze with LLM
        try:
            result = self._analyze_command(command)
            if result.get("dangerous", True):
                reason = result.get("reason", "Command flagged as dangerous")
                category = result.get("category", "unknown")
                return ErrorResult(
                    error=f"Dangerous command blocked (category: {category}): {reason}"
                )
            return SuccessResult()
        except Exception as e:
            # On LLM failure, use fallback behavior
            fallback = getattr(settings, "DANGEROUS_COMMAND_FALLBACK", "block")
            if fallback == "block":
                return ErrorResult(
                    error=f"Failed to analyze command safety: {e}. Command blocked as precaution."
                )
            # If fallback is "allow", let it through
            return SuccessResult()

    def _analyze_command(self, command: str) -> dict[str, str | bool]:
        """Use LLM to analyze if command is dangerous.

        Returns a dict with keys: dangerous (bool), reason (str), category (str)
        """
        model = getattr(settings, "DANGEROUS_COMMAND_MODEL", "gpt-4o-mini")
        timeout = getattr(settings, "DANGEROUS_COMMAND_TIMEOUT", 10)

        client = get_client()

        prompt = DANGEROUS_COMMAND_PROMPT.format(command=command)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0,
            timeout=timeout,
        )

        content = response.choices[0].message.content or ""
        return self._parse_response(content)

    def _parse_response(self, content: str) -> dict[str, str | bool]:
        """Parse LLM response into structured result."""
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last line if they're code fence markers
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            result = json.loads(content)
            # Validate expected keys
            if "dangerous" not in result:
                result["dangerous"] = True  # Conservative default
            return result
        except json.JSONDecodeError:
            # If we can't parse, treat as dangerous (conservative)
            return {
                "dangerous": True,
                "reason": "Could not parse LLM response",
                "category": "parse_error",
            }
