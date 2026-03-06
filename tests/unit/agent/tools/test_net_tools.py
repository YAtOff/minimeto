from unittest.mock import MagicMock, patch

import httpx
import pytest

from meto.agent.context import Context
from meto.agent.tools.net_tools import fetch, handle_fetch


@pytest.fixture
def mock_context():
    return MagicMock(spec=Context)


def test_fetch_success(mock_context):
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.content = b"web page content"
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        result = fetch(mock_context, "https://example.com")
        assert result == "web page content"
        mock_client.get.assert_called_once_with(
            "https://example.com", headers={"User-Agent": "meto/0"}
        )


def test_fetch_invalid_scheme(mock_context):
    result = fetch(mock_context, "ftp://example.com")
    assert "Error fetching" in result
    assert "unsupported URL scheme 'ftp'" in result


def test_fetch_http_error(mock_context):
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        result = fetch(mock_context, "https://example.com/notfound")
        assert "Error fetching" in result
        assert "404 Not Found" in result


def test_handle_fetch(mock_context):
    with patch("meto.agent.tools.net_tools.fetch") as mock_fetch:
        mock_fetch.return_value = "content"
        params = {"url": "https://test.com", "max_bytes": 500}
        result = handle_fetch(mock_context, params)
        assert result == "content"
        mock_fetch.assert_called_once_with(mock_context, "https://test.com", 500)
