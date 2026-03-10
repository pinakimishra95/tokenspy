"""Tests for tokenspy.tracing — Trace, Span, scores, and SQLite persistence."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

import tokenspy
from tokenspy.tracing import (
    Span,
    Trace,
    get_current_span_id,
    get_current_trace_id,
    span,
    trace,
    update_span_llm_data,
)


# ── Unit tests (no DB) ─────────────────────────────────────────────────────────

def test_trace_context_var_set_and_cleared():
    with trace("my-trace") as t:
        assert get_current_trace_id() == t.id
    assert get_current_trace_id() is None


def test_span_context_var_set_and_cleared():
    with trace("t"):
        with span("my-span") as s:
            assert get_current_span_id() == s.id
        assert get_current_span_id() is None


def test_span_inherits_trace_id():
    with trace("t") as t:
        with span("s") as s:
            assert s.trace_id == t.id


def test_nested_spans_parent_linking():
    with trace("t"):
        with span("outer") as outer:
            with span("inner") as inner:
                assert inner.parent_span_id == outer.id
                assert get_current_span_id() == inner.id
            assert get_current_span_id() == outer.id


def test_span_records_duration():
    with trace("t"):
        with span("s") as s:
            time.sleep(0.01)
    assert s.end_time is not None
    assert s.end_time > s.start_time


def test_span_update():
    with trace("t"):
        with span("s") as s:
            s.update(output="hello", metadata={"k": "v"})
    assert s.output == "hello"
    assert s.metadata == {"k": "v"}


def test_span_status_error_on_exception():
    with trace("t"):
        try:
            with span("bad") as s:
                raise ValueError("oops")
        except ValueError:
            pass
    assert s._status == "error"


def test_trace_score_no_db():
    """score() should not crash when no DB is configured."""
    with trace("t") as t:
        t.score("quality", 0.9)


def test_update_span_llm_data_no_crash_when_no_span():
    """update_span_llm_data should be a no-op when called outside a span."""
    update_span_llm_data(
        span_id="nonexistent",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        duration_ms=200.0,
    )


# ── Integration tests (with SQLite) ───────────────────────────────────────────

@pytest.fixture()
def db_tracker(tmp_path: Path):
    """Global tracker backed by a temp SQLite DB. Restored after test."""
    from tokenspy.tracker import Tracker, get_global_tracker, set_global_tracker
    db = tmp_path / "test.db"
    t = Tracker(persist_path=db)
    prev = get_global_tracker()
    set_global_tracker(t)
    yield t, db
    set_global_tracker(prev)


def test_trace_persisted_to_db(db_tracker):
    import sqlite3
    _tracker, db = db_tracker

    with trace("pipeline") as t:
        with span("step1") as s:
            s.update(output="done")

    conn = sqlite3.connect(str(db))
    traces_row = conn.execute("SELECT id, name FROM traces WHERE id=?", (t.id,)).fetchone()
    spans_rows = conn.execute("SELECT id, name FROM spans WHERE trace_id=?", (t.id,)).fetchall()
    conn.close()

    assert traces_row is not None
    assert traces_row[1] == "pipeline"
    assert len(spans_rows) == 1
    assert spans_rows[0][1] == "step1"


def test_span_score_persisted(db_tracker):
    import sqlite3
    _tracker, db = db_tracker

    with trace("t") as t:
        t.score("relevance", 0.85, scorer="human", comment="looks good")

    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT name, value, comment FROM scores WHERE trace_id=?", (t.id,)
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0] == ("relevance", 0.85, "looks good")
