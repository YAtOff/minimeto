from meto.agent.autopilot.handover import extract_handover


def test_extract_handover_at_end():
    text = """Some assistant talk.
### 🎯 Task Completed: 1.1
#### Summary: Task done
#### Discoveries: None
"""
    handover = extract_handover(text)
    assert handover is not None
    assert "### 🎯 Task Completed: 1.1" in handover
    assert "#### Summary: Task done" in handover


def test_extract_handover_with_following_content():
    text = """### 🎯 Task Completed: 1.1
#### Summary: Done
### Some Other Header
More text.
"""
    handover = extract_handover(text)
    assert handover is not None
    assert "### 🎯 Task Completed: 1.1" in handover
    assert "### Some Other Header" not in handover


def test_extract_handover_not_found():
    text = "Just some text without handover."
    assert extract_handover(text) is None


def test_extract_handover_empty():
    assert extract_handover("") is None
    assert extract_handover(None) is None  # type: ignore
