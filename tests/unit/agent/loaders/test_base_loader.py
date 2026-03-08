import pytest
import yaml
from pathlib import Path
from meto.agent.loaders.base import BaseResourceLoader

class ConcreteLoader(BaseResourceLoader[str]):
    def discover(self) -> None:
        pass

def test_parse_resource_file_raises_unexpected_exceptions(tmp_path):
    loader = ConcreteLoader(tmp_path)
    test_file = tmp_path / "test.md"
    test_file.write_text("---\ntitle: test\n---\nbody")
    
    # Mock read_text to raise an unexpected exception
    with pytest.MonkeyPatch.context() as mp:
        def mock_read_text(*args, **kwargs):
            raise ValueError("Unexpected error")
        mp.setattr(Path, "read_text", mock_read_text)
        
        # Now it should raise instead of returning None
        with pytest.raises(ValueError, match="Unexpected error"):
            loader.parse_resource_file(test_file)

def test_parse_resource_file_handles_os_error(tmp_path):
    loader = ConcreteLoader(tmp_path)
    test_file = tmp_path / "test.md"
    test_file.write_text("---\ntitle: test\n---\nbody")
    
    with pytest.MonkeyPatch.context() as mp:
        def mock_read_text(*args, **kwargs):
            raise OSError("OS error")
        mp.setattr(Path, "read_text", mock_read_text)
        
        result = loader.parse_resource_file(test_file)
        assert result is None

def test_parse_resource_file_handles_yaml_error(tmp_path):
    loader = ConcreteLoader(tmp_path)
    test_file = tmp_path / "test.md"
    # Invalid YAML (missing closing bracket)
    test_file.write_text("---\ntools: [unclosed\n---\nbody")
    
    result = loader.parse_resource_file(test_file)
    assert result is None

def test_parse_resource_file_handles_unicode_error(tmp_path):
    loader = ConcreteLoader(tmp_path)
    test_file = tmp_path / "test.md"
    test_file.write_text("---\ntitle: test\n---\nbody")
    
    with pytest.MonkeyPatch.context() as mp:
        def mock_read_text(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        mp.setattr(Path, "read_text", mock_read_text)
        
        result = loader.parse_resource_file(test_file)
        assert result is None
