from pathlib import Path
from unittest.mock import MagicMock, patch

from meto.agent.reasoning_log import ConsoleWriter, JsonlWriter, MarkdownWriter, ReasoningLogger


def test_reasoning_logger_initialization():
    """Verify that ReasoningLogger initializes all writers."""
    with patch("meto.agent.reasoning_log.reasoning_log_file") as mock_log_file:
        mock_log_file.return_value = Path("test.jsonl")
        with patch("meto.agent.reasoning_log.logging.FileHandler"):
            with patch("builtins.open", MagicMock()):
                logger = ReasoningLogger("test-agent")
                assert len(logger.writers) == 3
                assert any(isinstance(w, ConsoleWriter) for w in logger.writers)
                assert any(isinstance(w, JsonlWriter) for w in logger.writers)
                assert any(isinstance(w, MarkdownWriter) for w in logger.writers)


def test_reasoning_logger_context_manager():
    """Verify that ReasoningLogger works as a context manager and calls close() on writers."""
    with patch("meto.agent.reasoning_log.reasoning_log_file") as mock_log_file:
        mock_log_file.return_value = Path("test.jsonl")
        with patch("meto.agent.reasoning_log.logging.FileHandler"):
            with patch("builtins.open", MagicMock()):
                with ReasoningLogger("test-agent") as logger:
                    # Mock the writers' close methods
                    for w in logger.writers:
                        w.close = MagicMock()

                    writers = logger.writers

                for w in writers:
                    w.close.assert_called_once()


def test_jsonl_writer_close():
    """Verify that JsonlWriter close() cleans up handlers."""
    with patch("meto.agent.reasoning_log.logging.FileHandler") as mock_handler:
        with patch("meto.agent.reasoning_log.reasoning_log_file") as mock_log_file:
            mock_log_file.return_value = Path("test.jsonl")

            writer = JsonlWriter("test-agent")
            handler_instance = mock_handler.return_value

            writer.close()

            # Verify close was called on the handler
            handler_instance.close.assert_called()
            assert writer._json_handler is None


def test_markdown_writer_initialization_and_close():
    """Verify that MarkdownWriter opens and closes its file."""
    with patch("meto.agent.reasoning_log.reasoning_log_file") as mock_log_file:
        mock_log_file.return_value = Path("test.jsonl")
        with patch("builtins.open") as mock_open:
            mock_file = mock_open.return_value

            writer = MarkdownWriter("test-agent")
            mock_open.assert_called_once_with(Path("test.md"), "a", encoding="utf-8")

            writer.close()
            mock_file.close.assert_called_once()
