"""Tests for tokenspy.eval.dataset."""
from __future__ import annotations

import json

import pytest

from tokenspy.eval.dataset import Dataset


@pytest.fixture()
def ds(tmp_path):
    """Dataset backed by a temp SQLite DB, with global tracker set."""
    from tokenspy.tracker import Tracker, get_global_tracker, set_global_tracker
    db = tmp_path / "test.db"
    tracker = Tracker(persist_path=db)
    prev = get_global_tracker()
    set_global_tracker(tracker)
    yield Dataset(name="test-ds", description="test dataset")
    set_global_tracker(prev)


def test_add_item(ds):
    item_id = ds.add(input={"q": "What is 2+2?"}, expected_output="4")
    assert isinstance(item_id, str)
    items = ds.items()
    assert len(items) == 1
    assert items[0].input == {"q": "What is 2+2?"}
    assert str(items[0].expected_output) == "4"


def test_add_multiple_items(ds):
    ds.add(input={"q": "a"}, expected_output="A")
    ds.add(input={"q": "b"}, expected_output="B")
    assert len(ds.items()) == 2


def test_len(ds):
    ds.add(input={"q": "x"})
    assert len(ds) == 1


def test_from_json(ds, tmp_path):
    data = [
        {"input": {"q": "France capital?"}, "expected_output": "Paris"},
        {"input": {"q": "Germany capital?"}, "expected_output": "Berlin"},
    ]
    json_file = tmp_path / "cases.json"
    json_file.write_text(json.dumps(data))
    ds.from_json(str(json_file))
    assert len(ds.items()) == 2


def test_to_json(ds, tmp_path):
    ds.add(input={"q": "hello"}, expected_output="world")
    out = tmp_path / "out.json"
    ds.to_json(str(out))
    loaded = json.loads(out.read_text())
    assert len(loaded) == 1
    assert loaded[0]["input"] == {"q": "hello"}


def test_repr(ds):
    assert "test-ds" in repr(ds)
