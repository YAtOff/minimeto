from meto.agent.hooks.security import SafeReadHook


def test_safe_read_hook_allowed_file():
    hook = SafeReadHook(tool_name="read_file", arguments={"path": "src/main.py"})
    result = hook.run()
    assert result.success


def test_safe_read_hook_forbidden_file():
    hook = SafeReadHook(tool_name="read_file", arguments={"path": ".env"})
    result = hook.run()
    assert not result.success
    assert "security reasons" in result.error


def test_safe_read_hook_forbidden_dir():
    hook = SafeReadHook(tool_name="read_file", arguments={"path": ".git/config"})
    result = hook.run()
    assert not result.success
    assert "security reasons" in result.error


def test_safe_read_hook_resolves_symlink(tmp_path):
    # Create a hidden .env file
    secret_file = tmp_path / ".env"
    secret_file.write_text("SECRET=123")

    # Create a symlink to it
    safe_link = tmp_path / "safe.txt"
    try:
        safe_link.symlink_to(secret_file)
    except (OSError, NotImplementedError):
        # Fallback for systems that don't support symlinks (like Windows without admin)
        import pytest

        pytest.skip("Symlinks not supported on this platform")

    hook = SafeReadHook(tool_name="read_file", arguments={"path": str(safe_link)})
    result = hook.run()
    assert not result.success
    assert "security reasons" in result.error


def test_safe_read_hook_no_path():
    hook = SafeReadHook(tool_name="read_file", arguments={})
    result = hook.run()
    assert result.success


def test_safe_read_hook_pattern_match():
    # Test different forbidden patterns
    forbidden_files = [".env.prod", "id_rsa", "config.key", "my.pem"]
    for f in forbidden_files:
        hook = SafeReadHook(tool_name="read_file", arguments={"path": f})
        result = hook.run()
        assert not result.success, f"File {f} should be blocked"
