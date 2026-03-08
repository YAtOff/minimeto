import pytest
from pathlib import Path
from meto.agent.session import Session
from meto.agent.exceptions import SessionNotFoundError

def test_session_load_non_existent_raises(tmp_path):
    session_id = "non-existent"
    session_dir = tmp_path
    
    with pytest.raises(SessionNotFoundError) as excinfo:
        Session.load(session_id, session_dir=session_dir)
    
    assert f"Session '{session_id}' not found" in str(excinfo.value)

def test_session_new_creates_unique_ids():
    s1 = Session.new()
    s2 = Session.new()
    assert s1.session_id != s2.session_id
