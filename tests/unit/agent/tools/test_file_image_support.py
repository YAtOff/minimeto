import base64
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from meto.agent.context import Context
from meto.agent.tools.file_tools import read_file

@pytest.fixture
def mock_context():
    return MagicMock(spec=Context)

def test_read_file_image_support(mock_context):
    image_path = Path("tests/data/pixel.png")
    # Ensure the file exists
    assert image_path.exists()
    
    result = read_file(mock_context, str(image_path))
    
    # The expected format is __METO_IMAGE__:data:image/png;base64,<data>
    assert result.startswith("__METO_IMAGE__:data:image/png;base64,")
    
    # Verify base64 content
    header, encoded_data = result.split(",", 1)
    decoded_data = base64.b64decode(encoded_data)
    
    with open(image_path, "rb") as f:
        original_data = f.read()
    
    assert decoded_data == original_data
