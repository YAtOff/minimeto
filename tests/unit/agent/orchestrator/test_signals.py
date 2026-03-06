import signal
from unittest.mock import ANY, patch

from meto.agent.orchestrator.signals import InterruptSignal, handle_interrupt


def test_interrupt_signal():
    state = InterruptSignal()
    assert not state
    state.trigger()
    assert state


def test_handle_interrupt_context_manager():
    with patch("signal.signal") as mock_signal:
        mock_signal.return_value = "old_handler"

        with handle_interrupt() as state:
            assert isinstance(state, InterruptSignal)
            mock_signal.assert_called_once_with(signal.SIGINT, ANY)

            # Simulate a signal being received by calling the handler that was set
            handler = mock_signal.call_args[0][1]
            handler(signal.SIGINT, None)
            assert state.interrupted

        # Should restore the original handler
        mock_signal.assert_any_call(signal.SIGINT, "old_handler")
