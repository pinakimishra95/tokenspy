"""Tests for tokenspy.prompts — PromptRegistry and Prompt."""
from __future__ import annotations

import pytest

from tokenspy.prompts import PromptRegistry


@pytest.fixture()
def registry(tmp_path):
    """Fresh PromptRegistry backed by a temp DB with global tracker set."""
    from tokenspy.tracker import Tracker, get_global_tracker, set_global_tracker
    db = tmp_path / "test.db"
    tracker = Tracker(persist_path=db)
    prev = get_global_tracker()
    set_global_tracker(tracker)
    yield PromptRegistry()
    set_global_tracker(prev)


def test_push_creates_version(registry):
    p = registry.push("greeter", "Hello, {{name}}!")
    assert p.version == 1
    assert p.content == "Hello, {{name}}!"
    assert p.name == "greeter"


def test_push_auto_increments(registry):
    registry.push("greeter", "v1 {{name}}")
    p2 = registry.push("greeter", "v2 {{name}}")
    assert p2.version == 2


def test_pull_latest(registry):
    registry.push("greeter", "v1")
    registry.push("greeter", "v2")
    p = registry.pull("greeter")
    assert p.content == "v2"
    assert p.version == 2


def test_pull_specific_version(registry):
    registry.push("greeter", "v1")
    registry.push("greeter", "v2")
    p = registry.pull("greeter", version=1)
    assert p.content == "v1"


def test_pull_missing_raises(registry):
    with pytest.raises(KeyError):
        registry.pull("nonexistent")


def test_compile_simple(registry):
    registry.push("tmpl", "Hello, {{name}}! You have {{count}} messages.")
    p = registry.pull("tmpl")
    result = p.compile(name="Alice", count=3)
    assert result == "Hello, Alice! You have 3 messages."


def test_compile_missing_var_warns(registry):
    registry.push("tmpl", "Hello, {{name}}!")
    p = registry.pull("tmpl")
    with pytest.warns(UserWarning, match="unset"):
        result = p.compile()
    assert "{{name}}" in result or result == "Hello, !"


def test_set_production(registry):
    registry.push("greeter", "v1")
    registry.push("greeter", "v2")
    registry.set_production("greeter", version=1)
    p = registry.pull("greeter", label="production")
    assert p.version == 1


def test_list_prompts(registry):
    registry.push("a", "content a")
    registry.push("b", "content b")
    listing = registry.list()
    names = [item["name"] for item in listing]
    assert "a" in names
    assert "b" in names


def test_delete_version(registry):
    registry.push("greeter", "v1")
    registry.push("greeter", "v2")
    registry.delete("greeter", version=1)
    with pytest.raises(KeyError):
        registry.pull("greeter", version=1)
    # v2 should still be there
    p = registry.pull("greeter", version=2)
    assert p.version == 2
