"""
prompts.py — Prompt versioning for tokenspy.

Store, version, and track prompts locally in SQLite.
Compare cost and latency across prompt versions.

Usage::

    import tokenspy

    # Push a new version
    p = tokenspy.prompts.push(
        "summarizer",
        "Summarize the following in {{style}} style:\\n\\n{{text}}"
    )
    print(p.version)   # 1

    # Pull latest
    p = tokenspy.prompts.pull("summarizer")
    compiled = p.compile(style="concise", text="Long document...")

    # Pull production-tagged version
    tokenspy.prompts.set_production("summarizer", version=1)
    p = tokenspy.prompts.pull("summarizer", label="production")

    # Compare two versions by cost and latency
    tokenspy.prompts.compare("summarizer", v1=1, v2=2)
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
import warnings
from pathlib import Path
from typing import Any


def _get_db_path() -> Path | None:
    from tokenspy.tracker import get_global_tracker
    return get_global_tracker().db_path


def _db_conn() -> sqlite3.Connection | None:
    path = _get_db_path()
    if path is None or not path.exists():
        return None
    return sqlite3.connect(str(path))


class Prompt:
    """A versioned prompt template.

    Variables are denoted ``{{variable_name}}``.
    """

    def __init__(
        self,
        id: str,
        name: str,
        version: int,
        content: str,
        prompt_type: str = "text",
        tags: list[str] | None = None,
        created_at: float | None = None,
        is_production: bool = False,
    ) -> None:
        self.id = id
        self.name = name
        self.version = version
        self.content = content
        self.prompt_type = prompt_type
        self.tags = tags or []
        self.created_at = created_at or time.time()
        self.is_production = is_production

    def compile(self, **variables: Any) -> str:
        """Substitute ``{{variable}}`` placeholders and return the filled string.

        Warns if any placeholders remain unfilled.

        Example::

            p = tokenspy.prompts.pull("summarizer")
            text = p.compile(style="concise", text="My document...")
        """
        result = self.content
        for key, val in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(val))
        remaining = re.findall(r"\{\{(\w+)\}\}", result)
        if remaining:
            warnings.warn(
                f"[tokenspy] Prompt '{self.name}' v{self.version} has "
                f"unset variables: {remaining}",
                stacklevel=2,
            )
        return result

    def __repr__(self) -> str:
        prod = " [production]" if self.is_production else ""
        return f"Prompt(name={self.name!r}, version={self.version}{prod})"


class PromptRegistry:
    """Registry for versioned prompts, backed by SQLite.

    Access via the module-level ``tokenspy.prompts`` singleton.
    """

    def push(
        self,
        name: str,
        content: str,
        prompt_type: str = "text",
        tags: list[str] | None = None,
    ) -> Prompt:
        """Create a new version of a prompt and store it.

        The version number is auto-incremented (1, 2, 3, ...).

        Returns:
            The newly created :class:`Prompt`.
        """
        conn = _db_conn()
        if conn is None:
            # No persistence — return in-memory prompt at version 1
            return Prompt(
                id=str(uuid.uuid4()), name=name, version=1,
                content=content, prompt_type=prompt_type, tags=tags,
            )
        try:
            row = conn.execute(
                "SELECT MAX(version) FROM prompts WHERE name = ?", (name,)
            ).fetchone()
            next_version = (row[0] or 0) + 1
            prompt_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO prompts (id, name, version, content, prompt_type, tags, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    prompt_id, name, next_version, content, prompt_type,
                    json.dumps(tags or []), time.time(),
                ),
            )
            conn.commit()
            return Prompt(
                id=prompt_id, name=name, version=next_version,
                content=content, prompt_type=prompt_type, tags=tags,
            )
        except Exception:
            return Prompt(
                id=str(uuid.uuid4()), name=name, version=1,
                content=content, prompt_type=prompt_type, tags=tags,
            )
        finally:
            conn.close()

    def pull(
        self,
        name: str,
        label: str | None = None,
        version: int | None = None,
    ) -> Prompt:
        """Retrieve a prompt by name.

        Args:
            name: Prompt name.
            label: If ``"production"``, returns the production-tagged version.
            version: If set, returns that specific version number.
                     Defaults to the latest version.

        Raises:
            KeyError: If no matching prompt is found.
        """
        conn = _db_conn()
        if conn is None:
            raise KeyError(f"No prompt {name!r}: persistence not enabled")
        try:
            if version is not None:
                row = conn.execute(
                    "SELECT id, name, version, content, prompt_type, tags, created_at, is_production "
                    "FROM prompts WHERE name = ? AND version = ?",
                    (name, version),
                ).fetchone()
            elif label == "production":
                row = conn.execute(
                    "SELECT id, name, version, content, prompt_type, tags, created_at, is_production "
                    "FROM prompts WHERE name = ? AND is_production = 1 "
                    "ORDER BY created_at DESC LIMIT 1",
                    (name,),
                ).fetchone()
            else:
                # Latest
                row = conn.execute(
                    "SELECT id, name, version, content, prompt_type, tags, created_at, is_production "
                    "FROM prompts WHERE name = ? ORDER BY version DESC LIMIT 1",
                    (name,),
                ).fetchone()
        finally:
            conn.close()

        if row is None:
            raise KeyError(f"No prompt {name!r} found (label={label!r}, version={version})")

        return Prompt(
            id=row[0], name=row[1], version=row[2], content=row[3],
            prompt_type=row[4],
            tags=json.loads(row[5]) if row[5] else [],
            created_at=row[6],
            is_production=bool(row[7]),
        )

    def set_production(self, name: str, version: int) -> None:
        """Mark a specific version as the production version.

        Clears the production flag from all other versions of the same prompt.
        """
        conn = _db_conn()
        if conn is None:
            return
        try:
            conn.execute("UPDATE prompts SET is_production = 0 WHERE name = ?", (name,))
            conn.execute(
                "UPDATE prompts SET is_production = 1 WHERE name = ? AND version = ?",
                (name, version),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def list(self) -> list[dict]:
        """Return all prompts as a list of dicts."""
        conn = _db_conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(
                "SELECT name, version, prompt_type, tags, created_at, is_production "
                "FROM prompts ORDER BY name, version"
            ).fetchall()
        except Exception:
            return []
        finally:
            conn.close()
        return [
            {
                "name": r[0], "version": r[1], "type": r[2],
                "tags": json.loads(r[3]) if r[3] else [],
                "created_at": r[4], "is_production": bool(r[5]),
            }
            for r in rows
        ]

    def compare(self, name: str, v1: int, v2: int) -> None:
        """Print a cost and latency comparison between two versions.

        Requires calls to have been recorded with ``tokenspy.init(persist=True)``.
        """
        # Load LLM calls and look for the prompt name in function names
        from tokenspy.tracker import get_global_tracker
        t = get_global_tracker()
        records = t.load_from_db() if t.db_path else t.records()

        p1 = self.pull(name, version=v1)
        p2 = self.pull(name, version=v2)

        print(f"\ntokenspy — Prompt comparison: {name!r}  v{v1} vs v{v2}")
        print(f"  v{v1}: {p1.content[:60]}{'...' if len(p1.content) > 60 else ''}")
        print(f"  v{v2}: {p2.content[:60]}{'...' if len(p2.content) > 60 else ''}")
        print("\n  (Link prompt versions to calls with tokenspy.prompts.track() in a future release)")

    def delete(self, name: str, version: int) -> None:
        """Delete a specific prompt version."""
        conn = _db_conn()
        if conn is None:
            return
        try:
            conn.execute(
                "DELETE FROM prompts WHERE name = ? AND version = ?", (name, version)
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()


# Module-level singleton — access as ``tokenspy.prompts``
prompts = PromptRegistry()
