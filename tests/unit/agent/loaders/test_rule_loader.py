from pathlib import Path
import pytest
from meto.agent.loaders.rule_loader import RuleMetadata

def test_rule_metadata_validation():
    # Valid
    RuleMetadata(
        name="test",
        description="test",
        patterns=["*.py"],
        path=Path("test.md"),
        content="test"
    )

    # Empty patterns
    with pytest.raises(ValueError, match="must have at least one pattern"):
        RuleMetadata(
            name="test",
            description="test",
            patterns=[],
            path=Path("test.md"),
            content="test"
        )
