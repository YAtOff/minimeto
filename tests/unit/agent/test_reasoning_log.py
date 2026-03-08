import logging
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from meto.agent.reasoning_log import ReasoningLogger

def test_reasoning_logger_context_manager():
    """Verify that ReasoningLogger works as a context manager and calls close()."""
    with patch("meto.agent.reasoning_log.logging.FileHandler") as mock_handler:
        with patch("meto.agent.reasoning_log.reasoning_log_file") as mock_log_file:
            mock_log_file.return_value = Path("test.jsonl")
            
            with ReasoningLogger("test-agent") as logger:
                # Check that handler was created
                mock_handler.assert_called_once()
                handler_instance = mock_handler.return_value
                
                # Verify logger is the one returned
                assert logger.agent_name == "test-agent"
                
            # Verify close was called on the handler
            handler_instance.close.assert_called()

def test_reasoning_logger_explicit_close():
    """Verify that close() cleans up handlers."""
    with patch("meto.agent.reasoning_log.logging.FileHandler") as mock_handler:
        with patch("meto.agent.reasoning_log.reasoning_log_file") as mock_log_file:
            mock_log_file.return_value = Path("test.jsonl")
            
            logger = ReasoningLogger("test-agent")
            handler_instance = mock_handler.return_value
            
            logger.close()
            
            # Verify close was called on the handler
            handler_instance.close.assert_called()
            assert logger._json_handler is None
