"""LLM client management and configuration."""

from functools import lru_cache

from openai import OpenAI

from meto.conf import settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """Create (and cache) an OpenAI client configured for the LiteLLM proxy.

    Raises:
        RuntimeError: If the API key is not configured.
    """
    if not settings.LLM_API_KEY:
        raise RuntimeError(
            "METO_LLM_API_KEY is not set. Configure it in .env or environment variables."
        )
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
