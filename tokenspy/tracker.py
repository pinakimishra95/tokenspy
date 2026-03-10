"""
tracker.py — Records LLM API call data.

CallRecord holds a single intercepted call. Tracker accumulates them
in memory and optionally persists to SQLite.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CallRecord:
    """One intercepted LLM API call."""

    function_name: str          # decorated function that triggered the call
    call_stack: list[str]       # simplified call stack for flame graph
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    # Optional metadata
    provider: str = "unknown"   # "anthropic" | "openai" | "google" | "langchain"
    session_id: str | None = None
    git_commit: str | None = None  # populated when track_git=True

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Tracker:
    """Thread-safe accumulator for CallRecords.

    Usage:
        tracker = Tracker()
        tracker.record(CallRecord(...))
        records = tracker.records()
        tracker.reset()
    """

    def __init__(self, persist_path: Path | None = None) -> None:
        self._records: list[CallRecord] = []
        self._lock = threading.Lock()
        self._persist_path = persist_path
        self._post_record_hooks: list[Callable[[CallRecord], None]] = []
        self._git_commit: str | None = None  # set by init(track_git=True)
        if persist_path:
            self._init_db(persist_path)

    @property
    def db_path(self) -> Path | None:
        """Path to the SQLite database, or None if persistence is disabled."""
        return self._persist_path

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, rec: CallRecord) -> None:
        # Stamp git commit if tracking is enabled
        if self._git_commit and rec.git_commit is None:
            rec.git_commit = self._git_commit
        with self._lock:
            self._records.append(rec)
            llm_call_id: int | None = None
        if self._persist_path:
            llm_call_id = self._save_to_db(rec)
        # Auto-link to active span in the tracing module (if any)
        try:
            from tokenspy.tracing import get_current_span_id, update_span_llm_data
            span_id = get_current_span_id()
            if span_id:
                update_span_llm_data(
                    span_id=span_id,
                    model=rec.model,
                    input_tokens=rec.input_tokens,
                    output_tokens=rec.output_tokens,
                    cost_usd=rec.cost_usd,
                    duration_ms=rec.duration_ms,
                    llm_call_id=llm_call_id,
                )
        except Exception:
            pass  # tracing not configured — silently skip
        # Call hooks outside the lock to avoid deadlocks.
        # BaseException subclasses (e.g. BudgetExceededError) propagate freely;
        # ordinary Exception subclasses from misbehaving hooks are suppressed.
        for hook in list(self._post_record_hooks):
            try:
                hook(rec)
            except Exception:
                pass  # suppress unexpected hook errors, but not BaseException

    def records(self) -> list[CallRecord]:
        with self._lock:
            return list(self._records)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    # ── Aggregate stats ────────────────────────────────────────────────────────

    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.records())

    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records())

    def total_calls(self) -> int:
        return len(self.records())

    def cost_by_function(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for r in self.records():
            result[r.function_name] = result.get(r.function_name, 0.0) + r.cost_usd
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def cost_by_model(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for r in self.records():
            result[r.model] = result.get(r.model, 0.0) + r.cost_usd
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def summary(self) -> dict:
        records = self.records()
        return {
            "total_cost_usd": self.total_cost(),
            "total_tokens": self.total_tokens(),
            "total_calls": len(records),
            "calls": [
                {
                    "function": r.function_name,
                    "model": r.model,
                    "provider": r.provider,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": r.cost_usd,
                    "duration_ms": r.duration_ms,
                    "timestamp": r.timestamp,
                    "call_stack": r.call_stack,
                }
                for r in records
            ],
            "by_function": self.cost_by_function(),
            "by_model": self.cost_by_model(),
        }

    # ── SQLite persistence ─────────────────────────────────────────────────────

    def _init_db(self, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Read-only filesystem or permission denied — disable persistence silently
            self._persist_path = None
            return
        conn = sqlite3.connect(str(path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                function_name TEXT,
                call_stack TEXT,
                model TEXT,
                provider TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost_usd REAL,
                duration_ms REAL,
                timestamp REAL,
                session_id TEXT
            )
        """)
        # Migrate: add git_commit column if it doesn't exist yet
        try:
            conn.execute("ALTER TABLE llm_calls ADD COLUMN git_commit TEXT")
        except Exception:
            pass  # column already exists
        conn.commit()
        self._init_new_tables(conn)
        conn.close()

    def _init_new_tables(self, conn: sqlite3.Connection) -> None:
        """Create v0.2.0 tables for tracing, evaluations, and prompts."""
        stmts = [
            """CREATE TABLE IF NOT EXISTS traces (
                id          TEXT PRIMARY KEY,
                name        TEXT,
                start_time  REAL,
                end_time    REAL,
                input       TEXT,
                output      TEXT,
                metadata    TEXT,
                tags        TEXT,
                user_id     TEXT,
                session_id  TEXT,
                git_commit  TEXT,
                error       TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS spans (
                id             TEXT PRIMARY KEY,
                trace_id       TEXT REFERENCES traces(id),
                parent_span_id TEXT,
                name           TEXT,
                span_type      TEXT,
                start_time     REAL,
                end_time       REAL,
                input          TEXT,
                output         TEXT,
                metadata       TEXT,
                model          TEXT,
                input_tokens   INTEGER,
                output_tokens  INTEGER,
                cost_usd       REAL,
                duration_ms    REAL,
                llm_call_id    INTEGER,
                status         TEXT DEFAULT 'ok'
            )""",
            """CREATE TABLE IF NOT EXISTS scores (
                id         TEXT PRIMARY KEY,
                trace_id   TEXT REFERENCES traces(id),
                span_id    TEXT,
                name       TEXT,
                value      REAL,
                comment    TEXT,
                scorer     TEXT,
                created_at REAL
            )""",
            """CREATE TABLE IF NOT EXISTS datasets (
                id          TEXT PRIMARY KEY,
                name        TEXT UNIQUE,
                description TEXT,
                created_at  REAL
            )""",
            """CREATE TABLE IF NOT EXISTS dataset_items (
                id              TEXT PRIMARY KEY,
                dataset_id      TEXT REFERENCES datasets(id),
                input           TEXT,
                expected_output TEXT,
                metadata        TEXT,
                created_at      REAL
            )""",
            """CREATE TABLE IF NOT EXISTS experiments (
                id            TEXT PRIMARY KEY,
                name          TEXT,
                dataset_id    TEXT REFERENCES datasets(id),
                function_name TEXT,
                created_at    REAL,
                git_commit    TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS experiment_results (
                id               TEXT PRIMARY KEY,
                experiment_id    TEXT REFERENCES experiments(id),
                dataset_item_id  TEXT REFERENCES dataset_items(id),
                output           TEXT,
                scores           TEXT,
                passed           INTEGER,
                error            TEXT,
                cost_usd         REAL,
                duration_ms      REAL
            )""",
            """CREATE TABLE IF NOT EXISTS prompts (
                id            TEXT PRIMARY KEY,
                name          TEXT,
                version       INTEGER,
                content       TEXT,
                prompt_type   TEXT,
                tags          TEXT,
                created_at    REAL,
                is_production INTEGER DEFAULT 0,
                UNIQUE(name, version)
            )""",
        ]
        for stmt in stmts:
            try:
                conn.execute(stmt)
            except Exception:
                pass
        conn.commit()

    def _save_to_db(self, rec: CallRecord) -> int | None:
        """Persist record and return the inserted row ID (for span linking)."""
        import json

        try:
            conn = sqlite3.connect(str(self._persist_path))
            cursor = conn.execute(
                """
                INSERT INTO llm_calls
                    (function_name, call_stack, model, provider,
                     input_tokens, output_tokens, cost_usd, duration_ms,
                     timestamp, session_id, git_commit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.function_name,
                    json.dumps(rec.call_stack),
                    rec.model,
                    rec.provider,
                    rec.input_tokens,
                    rec.output_tokens,
                    rec.cost_usd,
                    rec.duration_ms,
                    rec.timestamp,
                    rec.session_id,
                    rec.git_commit,
                ),
            )
            row_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return row_id
        except Exception:
            return None  # never crash the user's code due to tracking failure

    def load_from_db(self) -> list[CallRecord]:
        """Load all historical records from the SQLite database."""
        import json

        if not self._persist_path or not self._persist_path.exists():
            return []
        try:
            conn = sqlite3.connect(str(self._persist_path))
            rows = conn.execute(
                "SELECT function_name, call_stack, model, provider, "
                "input_tokens, output_tokens, cost_usd, duration_ms, "
                "timestamp, session_id, git_commit FROM llm_calls ORDER BY timestamp"
            ).fetchall()
            conn.close()
        except Exception:
            return []

        result = []
        for row in rows:
            try:
                result.append(
                    CallRecord(
                        function_name=row[0],
                        call_stack=json.loads(row[1]),
                        model=row[2],
                        provider=row[3],
                        input_tokens=row[4],
                        output_tokens=row[5],
                        cost_usd=row[6],
                        duration_ms=row[7],
                        timestamp=row[8],
                        session_id=row[9],
                        git_commit=row[10] if len(row) > 10 else None,
                    )
                )
            except Exception:
                continue
        return result


# ── Global default tracker ─────────────────────────────────────────────────────

_global_tracker: Tracker = Tracker()


def get_global_tracker() -> Tracker:
    return _global_tracker


def set_global_tracker(tracker: Tracker) -> None:
    global _global_tracker
    _global_tracker = tracker
