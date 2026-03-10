"""
tracing.py — Structured tracing with Trace + Span context managers.

Provides Langfuse-style observability without any cloud or proxy.
All data is stored in the local SQLite database.

Usage::

    with tokenspy.trace("research_pipeline", input={"query": q}) as t:
        with tokenspy.span("retrieve", span_type="retrieval") as s:
            docs = vector_store.search(q)
            s.update(output=docs, metadata={"n_docs": len(docs)})
        with tokenspy.span("generate", span_type="llm") as s:
            answer = client.chat.completions.create(...)
        t.update(output=answer)

    t.score("relevance", 0.92)
    t.score("hallucination", 0.05, scorer="llm_judge", comment="Clean output")
"""

from __future__ import annotations

import contextvars
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

# ── Context variables ──────────────────────────────────────────────────────────
# These propagate through async and threaded code automatically.

_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tokenspy_trace_id", default=None
)
_current_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tokenspy_span_id", default=None
)


def get_current_trace_id() -> str | None:
    return _current_trace_id.get()


def get_current_span_id() -> str | None:
    return _current_span_id.get()


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _get_db_path() -> Path | None:
    from tokenspy.tracker import get_global_tracker
    return get_global_tracker().db_path


def _db_conn() -> sqlite3.Connection | None:
    path = _get_db_path()
    if path is None or not path.exists():
        return None
    return sqlite3.connect(str(path))


# ── Span ───────────────────────────────────────────────────────────────────────

class Span:
    """A single operation within a trace.

    Created via ``tokenspy.span()`` context manager.
    """

    def __init__(
        self,
        name: str,
        span_type: str = "function",
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        input: Any = None,
        metadata: dict | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.name = name
        self.span_type = span_type
        self.start_time = time.time()
        self.end_time: float | None = None
        self._input = input
        self._output: Any = None
        self._metadata: dict = metadata or {}
        self._status = "ok"
        self._token: contextvars.Token | None = None

    @property
    def output(self) -> Any:
        return self._output

    @property
    def metadata(self) -> dict:
        return self._metadata

    def update(self, output: Any = None, metadata: dict | None = None) -> None:
        """Update span output and/or metadata mid-flight or after completion."""
        if output is not None:
            self._output = output
        if metadata:
            self._metadata.update(metadata)

    def __enter__(self) -> "Span":
        # Inherit trace_id from context if not set
        if self.trace_id is None:
            self.trace_id = _current_trace_id.get()
        if self.parent_span_id is None:
            self.parent_span_id = _current_span_id.get()
        self._token = _current_span_id.set(self.id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._status = "error"
        self.end_time = time.time()
        if self._token is not None:
            _current_span_id.reset(self._token)
        _persist_span(self)

    def __repr__(self) -> str:
        dur = f"{(self.end_time - self.start_time) * 1000:.1f}ms" if self.end_time else "running"
        return f"Span(name={self.name!r}, type={self.span_type!r}, {dur})"


# ── Trace ──────────────────────────────────────────────────────────────────────

class Trace:
    """Top-level container grouping a set of related spans.

    Created via ``tokenspy.trace()`` context manager.
    """

    def __init__(
        self,
        name: str,
        input: Any = None,
        tags: list[str] | None = None,
        user_id: str | None = None,
        metadata: dict | None = None,
        session_id: str | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.start_time = time.time()
        self.end_time: float | None = None
        self._input = input
        self._output: Any = None
        self._tags: list[str] = tags or []
        self._user_id = user_id
        self._metadata: dict = metadata or {}
        self._session_id = session_id
        self._error: str | None = None
        self._trace_token: contextvars.Token | None = None

    def update(self, output: Any = None, metadata: dict | None = None) -> None:
        """Update trace output and/or metadata."""
        if output is not None:
            self._output = output
        if metadata:
            self._metadata.update(metadata)

    def score(
        self,
        name: str,
        value: float,
        scorer: str = "human",
        comment: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """Attach a score to this trace (or a specific span).

        Args:
            name: Score name, e.g. "relevance", "hallucination".
            value: Numeric score, typically 0.0–1.0.
            scorer: Who/what produced the score: "human", "llm_judge", "code".
            comment: Optional explanation.
            span_id: If set, score is attached to that span instead of the trace.
        """
        _persist_score(
            score_id=str(uuid.uuid4()),
            trace_id=self.id,
            span_id=span_id,
            name=name,
            value=value,
            comment=comment,
            scorer=scorer,
        )

    def __enter__(self) -> "Trace":
        self._trace_token = _current_trace_id.set(self.id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            import traceback
            self._error = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        self.end_time = time.time()
        if self._trace_token is not None:
            _current_trace_id.reset(self._trace_token)
        _persist_trace(self)

    def __repr__(self) -> str:
        dur = f"{(self.end_time - self.start_time) * 1000:.1f}ms" if self.end_time else "running"
        return f"Trace(name={self.name!r}, {dur})"


# ── Persistence ────────────────────────────────────────────────────────────────

def _persist_trace(t: Trace) -> None:
    conn = _db_conn()
    if conn is None:
        return
    try:
        from tokenspy.tracker import get_global_tracker
        git = get_global_tracker()._git_commit

        conn.execute(
            """INSERT OR REPLACE INTO traces
               (id, name, start_time, end_time, input, output, metadata,
                tags, user_id, session_id, git_commit, error)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                t.id, t.name, t.start_time, t.end_time,
                _to_json(t._input), _to_json(t._output), _to_json(t._metadata),
                json.dumps(t._tags), t._user_id, t._session_id, git, t._error,
            ),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _persist_span(s: Span) -> None:
    conn = _db_conn()
    if conn is None:
        return
    try:
        conn.execute(
            """INSERT OR REPLACE INTO spans
               (id, trace_id, parent_span_id, name, span_type,
                start_time, end_time, input, output, metadata, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                s.id, s.trace_id, s.parent_span_id, s.name, s.span_type,
                s.start_time, s.end_time,
                _to_json(s._input), _to_json(s._output), _to_json(s._metadata),
                s._status,
            ),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _persist_score(
    score_id: str,
    trace_id: str,
    span_id: str | None,
    name: str,
    value: float,
    comment: str | None,
    scorer: str,
) -> None:
    conn = _db_conn()
    if conn is None:
        return
    try:
        conn.execute(
            """INSERT INTO scores (id, trace_id, span_id, name, value, comment, scorer, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (score_id, trace_id, span_id, name, value, comment, scorer, time.time()),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def update_span_llm_data(
    span_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_ms: float,
    llm_call_id: int | None = None,
) -> None:
    """Called by the tracker hook to link an LLM call to its enclosing span."""
    conn = _db_conn()
    if conn is None:
        return
    try:
        conn.execute(
            """UPDATE spans SET model=?, input_tokens=?, output_tokens=?,
               cost_usd=?, duration_ms=?, llm_call_id=? WHERE id=?""",
            (model, input_tokens, output_tokens, cost_usd, duration_ms, llm_call_id, span_id),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


# ── Public context managers ────────────────────────────────────────────────────

@contextmanager
def trace(
    name: str,
    input: Any = None,
    tags: list[str] | None = None,
    user_id: str | None = None,
    metadata: dict | None = None,
    session_id: str | None = None,
) -> Generator[Trace, None, None]:
    """Context manager that creates a top-level trace.

    Example::

        with tokenspy.trace("pipeline", input={"query": q}) as t:
            with tokenspy.span("retrieve") as s:
                docs = fetch(q)
                s.update(output=docs)
            t.update(output=answer)
        t.score("relevance", 0.9)
    """
    t = Trace(
        name=name, input=input, tags=tags,
        user_id=user_id, metadata=metadata, session_id=session_id,
    )
    with t:
        yield t


@contextmanager
def span(
    name: str,
    span_type: str = "function",
    input: Any = None,
    metadata: dict | None = None,
) -> Generator[Span, None, None]:
    """Context manager that creates a child span within the current trace.

    Example::

        with tokenspy.span("retrieve_docs", span_type="retrieval") as s:
            docs = vector_store.search(query)
            s.update(output=docs)
    """
    s = Span(name=name, span_type=span_type, input=input, metadata=metadata)
    with s:
        yield s


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except Exception:
        return str(value)
