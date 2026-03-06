from unittest.mock import patch

import pytest

from meto.agent.orchestrator.client import get_client


def test_get_client_success():
    with patch("meto.agent.orchestrator.client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-test"
        mock_settings.LLM_BASE_URL = "http://localhost:1234"

        # Clear lru_cache for testing
        get_client.cache_clear()

        with patch("meto.agent.orchestrator.client.OpenAI") as mock_openai:
            client = get_client()
            assert client is not None
            mock_openai.assert_called_once_with(api_key="sk-test", base_url="http://localhost:1234")


def test_get_client_no_api_key():
    with patch("meto.agent.orchestrator.client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = None

        # Clear lru_cache for testing
        get_client.cache_clear()

        with pytest.raises(RuntimeError) as excinfo:
            get_client()
        assert "METO_LLM_API_KEY is not set" in str(excinfo.value)
