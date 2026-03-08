import subprocess
from unittest.mock import patch
from meto.agent.shell import run_shell
from meto.conf import settings

def test_run_shell_timeout_message():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 10", timeout=settings.TOOL_TIMEOUT_SECONDS)):
        result = run_shell("sleep 10")
        assert f"(timeout after {settings.TOOL_TIMEOUT_SECONDS}s)" in result
        assert "METO_TOOL_TIMEOUT_SECONDS" in result
