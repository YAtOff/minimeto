from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def extract_handover(text: str) -> str | None:
    """Extract the autopilot handover block from LLM output.

    The block starts with '### 🎯 Task Completed' and continues until
    the end of the text or another top-level markdown heading.
    """
    if not text:
        return None

    try:
        # Look for the start of the handover block
        pattern = re.compile(
            r"### \U0001F3AF Task Completed:.*?\n(.*?)(?=\n### |$)",
            re.DOTALL | re.IGNORECASE,
        )

        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    except re.error as e:
        logger.error(f"Regex error extracting handover: {e}")

    return None
