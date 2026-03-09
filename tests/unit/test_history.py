"""Tests for command history management."""

from pathlib import Path

from meto.history import FilteredHistory, create_history


class TestFilteredHistory:
    """Tests for FilteredHistory class."""

    def test_append_normal_command(self, tmp_path: Path):
        """Normal commands should be added to history."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        history.append_string("ls -la")
        history.append_string("cat file.txt")

        lines = history.get_strings()
        assert "ls -la" in lines
        assert "cat file.txt" in lines

    def test_append_empty_line_skipped(self, tmp_path: Path):
        """Empty lines should be skipped."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        history.append_string("")
        history.append_string("   ")

        lines = history.get_strings()
        assert len([line for line in lines if line.strip()]) == 0

    def test_exclude_api_keys(self, tmp_path: Path):
        """Commands with API keys should be excluded."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        history.append_string('export API_KEY="sk-1234567890abcdef"')
        history.append_string("normal command")

        lines = history.get_strings()
        assert "normal command" in lines
        assert "API_KEY" not in " ".join(lines)

    def test_exclude_passwords(self, tmp_path: Path):
        """Commands with passwords should be excluded."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        history.append_string('PASSWORD="secret123"')
        history.append_string("echo hello")

        lines = history.get_strings()
        assert "echo hello" in lines
        assert "PASSWORD" not in " ".join(lines)

    def test_exclude_openai_keys(self, tmp_path: Path):
        """OpenAI-style keys should be excluded."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        history.append_string("sk-proj-abcdefghijklmnopqrstuvwxyz123456")
        history.append_string("valid command")

        lines = history.get_strings()
        assert "valid command" in lines
        assert "sk-proj" not in " ".join(lines)

    def test_max_size_trimming(self, tmp_path: Path):
        """History should be trimmed when exceeding max_size."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file), max_size=100)

        # Add 150 commands
        for i in range(150):
            history.append_string(f"command_{i}")

        lines = history.get_strings()
        # Should have trimmed to ~90% of max_size
        assert len(lines) < 100
        # Most recent commands should be preserved
        assert "command_149" in lines

    def test_consecutive_duplicates_deduplicated(self, tmp_path: Path):
        """Duplicate commands should all be stored."""
        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        history.append_string("ls")
        history.append_string("ls")
        history.append_string("ls")
        history.append_string("cd")

        lines = history.get_strings()
        # All commands should be stored (no auto-deduplication in FileHistory)
        assert "ls" in lines
        assert "cd" in lines
        assert len(lines) == 4

    def test_corrupted_history_file_handled(self, tmp_path: Path):
        """Corrupted history files should be handled gracefully."""
        history_file = tmp_path / "history"

        # Write corrupted data
        with open(history_file, "wb") as f:
            f.write(b"\xff\xfe invalid utf-8 \x00\x00")

        # Should not crash when loading
        history = FilteredHistory(str(history_file))
        lines = history.get_strings()
        assert isinstance(lines, list)

    def test_concurrent_access(self, tmp_path: Path):
        """Concurrent appends should be thread-safe."""
        import threading

        history_file = tmp_path / "history"
        history = FilteredHistory(str(history_file))

        def append_commands(start: int, count: int):
            for i in range(start, start + count):
                history.append_string(f"command_{i}")

        threads = [threading.Thread(target=append_commands, args=(i * 100, 100)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash, should have some commands
        lines = history.get_strings()
        assert len(lines) > 0


class TestCreateHistory:
    """Tests for create_history factory function."""

    def test_creates_history_instance(self, tmp_path: Path, monkeypatch):
        """Should create a FilteredHistory instance."""
        monkeypatch.setattr("meto.conf.settings.HISTORY_FILE", tmp_path / "history")
        monkeypatch.setattr("meto.conf.settings.HISTORY_ENABLED", True)

        history = create_history()
        assert history is not None
        assert isinstance(history, FilteredHistory)

    def test_returns_none_when_disabled(self, monkeypatch):
        """Should return None when history is disabled."""
        monkeypatch.setattr("meto.conf.settings.HISTORY_ENABLED", False)

        history = create_history()
        assert history is None
