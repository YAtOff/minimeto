from unittest.mock import MagicMock, patch

import openai
import pytest

from meto.agent.exceptions import LLMError
from meto.agent.orchestrator.client import get_client


def test_get_client_success():
    with patch("meto.agent.orchestrator.client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-test"
        mock_settings.LLM_BASE_URL = "http://localhost:1234"

        # Clear lru_cache for testing
        get_client.cache_clear()

        with patch("meto.agent.orchestrator.client.OpenAI") as mock_openai:
            client_instance = mock_openai.return_value
            client = get_client()

            assert client is not None
            mock_openai.assert_called_once_with(api_key="sk-test", base_url="http://localhost:1234")
            # Verify validation was called
            client_instance.models.list.assert_called_once()


def test_get_client_no_api_key():
    with patch("meto.agent.orchestrator.client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = None

        # Clear lru_cache for testing
        get_client.cache_clear()

        with pytest.raises(RuntimeError) as excinfo:
            get_client()
        assert "METO_LLM_API_KEY is not set" in str(excinfo.value)


def test_get_client_auth_failure():
    with patch("meto.agent.orchestrator.client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "invalid-key"
        mock_settings.LLM_BASE_URL = "http://localhost:1234"

        get_client.cache_clear()

        with patch("meto.agent.orchestrator.client.OpenAI") as mock_openai:
            client_instance = mock_openai.return_value
            # Mock authentication failure
            client_instance.models.list.side_effect = openai.AuthenticationError(
                message="Invalid API Key", response=MagicMock(), body={}
            )

            with pytest.raises(LLMError) as excinfo:
                get_client()
            assert "LLM authentication failed" in str(excinfo.value)
            assert "Check your METO_LLM_API_KEY" in str(excinfo.value)


def test_get_client_connection_failure():
    with patch("meto.agent.orchestrator.client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "sk-test"
        mock_settings.LLM_BASE_URL = "http://invalid-url"

        get_client.cache_clear()

        with patch("meto.agent.orchestrator.client.OpenAI") as mock_openai:
            client_instance = mock_openai.return_value
            # Mock connection failure
            client_instance.models.list.side_effect = openai.APIConnectionError(request=MagicMock())

            with pytest.raises(LLMError) as excinfo:
                get_client()
            assert "Could not connect to LLM provider" in str(excinfo.value)
            assert "METO_LLM_BASE_URL" in str(excinfo.value)
