"""Network operations."""

from typing import Any
from urllib.parse import urlparse

import httpx

from meto.agent.context import Context
from meto.agent.shell import truncate


def fetch(_context: Context, url: str, max_bytes: int = 100000) -> str:
    """Fetch URL via HTTP GET, return response body as text (truncated)."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return f"Error fetching {url}: unsupported URL scheme '{parsed.scheme}'"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers={"User-Agent": "meto/0"})
            response.raise_for_status()
            content = response.content[: max_bytes + 1]
            return truncate(content.decode("utf-8", errors="replace"), max_bytes)
    except httpx.HTTPStatusError as e:
        return f"Error fetching {url}: {e.response.status_code} {e.response.reason_phrase}"
    except httpx.TimeoutException:
        return f"Error fetching {url}: timeout after 10s"
    except httpx.HTTPError as e:
        return f"Error fetching {url}: {e}"
    except OSError as ex:
        return f"Error fetching {url}: {ex}"


def handle_fetch(context: Context, parameters: dict[str, Any]) -> str:
    """Handle URL fetching."""
    url = parameters.get("url", "")
    max_bytes = parameters.get("max_bytes", 100000)
    return fetch(context, url, max_bytes)
