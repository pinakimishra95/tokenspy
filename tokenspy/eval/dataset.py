"""
eval/dataset.py — Dataset and DatasetItem for golden test sets.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _get_db_path() -> Path | None:
    from tokenspy.tracker import get_global_tracker
    return get_global_tracker().db_path


def _db_conn() -> sqlite3.Connection | None:
    path = _get_db_path()
    if path is None:
        return None
    if not path.exists():
        # DB file doesn't exist yet — create a minimal one
        from tokenspy.tracker import get_global_tracker
        t = get_global_tracker()
        if t._persist_path:
            t._init_db(t._persist_path)
        else:
            return None
    return sqlite3.connect(str(path))


@dataclass
class DatasetItem:
    """A single row in a dataset."""
    id: str
    dataset_id: str
    input: Any            # dict, str, or any JSON-serialisable value
    expected_output: Any  # optional expected answer
    metadata: dict
    created_at: float


class Dataset:
    """A named collection of test cases stored in SQLite.

    Usage::

        ds = tokenspy.dataset("qa-golden")
        ds.add(input={"q": "Capital of France?"}, expected_output="Paris")
        ds.from_json("cases.json")
        for item in ds.items():
            print(item.input, item.expected_output)
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._id: str | None = None
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        conn = _db_conn()
        if conn is None:
            return
        try:
            row = conn.execute(
                "SELECT id FROM datasets WHERE name = ?", (self.name,)
            ).fetchone()
            if row:
                self._id = row[0]
            else:
                self._id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO datasets (id, name, description, created_at) VALUES (?,?,?,?)",
                    (self._id, self.name, self.description, time.time()),
                )
                conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def add(
        self,
        input: Any,
        expected_output: Any = None,
        metadata: dict | None = None,
    ) -> str:
        """Add a test case. Returns the item ID."""
        if self._id is None:
            self._ensure_exists()
        item_id = str(uuid.uuid4())
        conn = _db_conn()
        if conn is None:
            return item_id
        try:
            conn.execute(
                """INSERT INTO dataset_items
                   (id, dataset_id, input, expected_output, metadata, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    item_id, self._id,
                    _to_json(input), _to_json(expected_output),
                    json.dumps(metadata or {}), time.time(),
                ),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
        return item_id

    def items(self) -> list[DatasetItem]:
        """Return all items in the dataset."""
        if self._id is None:
            return []
        conn = _db_conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(
                "SELECT id, dataset_id, input, expected_output, metadata, created_at "
                "FROM dataset_items WHERE dataset_id = ? ORDER BY created_at",
                (self._id,),
            ).fetchall()
        except Exception:
            return []
        finally:
            conn.close()

        result = []
        for row in rows:
            try:
                result.append(DatasetItem(
                    id=row[0],
                    dataset_id=row[1],
                    input=_from_json(row[2]),
                    expected_output=_from_json(row[3]),
                    metadata=json.loads(row[4]) if row[4] else {},
                    created_at=row[5],
                ))
            except Exception:
                continue
        return result

    def from_json(self, path: str) -> Dataset:
        """Import items from a JSON file.

        Expected format: a list of objects with "input" and optionally
        "expected_output" and "metadata" keys::

            [
              {"input": {"q": "What is 2+2?"}, "expected_output": "4"},
              ...
            ]
        """
        with open(path) as f:
            items = json.load(f)
        for item in items:
            self.add(
                input=item.get("input", item),
                expected_output=item.get("expected_output"),
                metadata=item.get("metadata"),
            )
        return self

    def from_csv(self, path: str, input_col: str, expected_col: str | None = None) -> Dataset:
        """Import items from a CSV file."""
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add(
                    input=row[input_col],
                    expected_output=row.get(expected_col) if expected_col else None,
                    metadata={k: v for k, v in row.items()
                              if k not in (input_col, expected_col)},
                )
        return self

    def to_json(self, path: str) -> None:
        """Export all items to a JSON file."""
        items = [
            {
                "input": item.input,
                "expected_output": item.expected_output,
                "metadata": item.metadata,
            }
            for item in self.items()
        ]
        with open(path, "w") as f:
            json.dump(items, f, indent=2)

    def __len__(self) -> int:
        return len(self.items())

    def __repr__(self) -> str:
        return f"Dataset(name={self.name!r}, items={len(self)})"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except Exception:
        return str(value)


def _from_json(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value
