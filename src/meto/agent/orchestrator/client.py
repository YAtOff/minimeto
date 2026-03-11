"""LLM client management and configuration."""

from functools import lru_cache

import openai
from openai import OpenAI

from meto.agent.exceptions import LLMError
from meto.conf import settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """Create (and cache) an OpenAI client configured for the LiteLLM proxy.

    Raises:
        RuntimeError: If the API key is not configured.
        LLMError: If client validation or connectivity fails.
    """
    if not settings.LLM_API_KEY:
        raise RuntimeError(
            "METO_LLM_API_KEY is not set. Configure it in .env or environment variables."
        )

    try:
        client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        # Perform a lightweight validation call to catch configuration/network issues early.
        # This will only execute once per session due to @lru_cache.
        _validate_client(client)
        return client
    except Exception as e:
        # Re-wrap any errors during creation or validation into an LLMError with clear guidance
        if isinstance(e, openai.AuthenticationError):
            msg = f"LLM authentication failed: {e}. Check your METO_LLM_API_KEY."
        elif isinstance(e, openai.APIConnectionError):
            msg = f"Could not connect to LLM provider at {settings.LLM_BASE_URL}: {e}. Check your internet connection and METO_LLM_BASE_URL."
        else:
            msg = f"Failed to initialize or validate LLM client: {e}"
        raise LLMError(msg) from e


def _validate_client(client: OpenAI) -> None:
    """Check connectivity and credentials with a lightweight API call."""
    # models.list() is a cheap call that verifies both credentials and connectivity
    client.models.list()
