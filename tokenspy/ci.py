"""
ci.py — GitHub Actions cost annotation and PR cost diff.

Usage in a GitHub Actions workflow::

    - name: tokenspy cost report
      run: |
        python -c "
        from tokenspy.ci import annotate_cost_diff
        annotate_cost_diff('current.db', 'baseline.db')
        "

Or via CLI::

    tokenspy annotate --current current.db --baseline baseline.db

GitHub Actions annotations format:
  ::notice title=tokenspy::message
  ::warning title=tokenspy cost regression::message

Job summary is written to $GITHUB_STEP_SUMMARY automatically.
"""

from __future__ import annotations

import os
from pathlib import Path


def _is_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _gha_annotate(level: str, title: str, message: str) -> None:
    """Emit a GitHub Actions workflow command annotation."""
    safe_msg = message.replace("\n", "%0A").replace("\r", "%0D")
    print(f"::{level} title={title}::{safe_msg}")


def _write_step_summary(content: str) -> None:
    """Append content to $GITHUB_STEP_SUMMARY if running in GitHub Actions."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a") as f:
                f.write(content + "\n")
        except OSError:
            pass


def annotate_cost_diff(current_db: str, baseline_db: str | None = None) -> None:
    """Compare LLM costs between current run and baseline, emit GHA annotations.

    Args:
        current_db: Path to current run's SQLite database.
        baseline_db: Path to baseline SQLite database for comparison.
            If None or file doesn't exist, reports absolute costs only.
    """
    from tokenspy.tracker import Tracker

    current_path = Path(current_db)
    if not current_path.exists():
        print(f"[tokenspy] No DB found at {current_db}")
        return

    current = Tracker(persist_path=current_path)
    current._records = current.load_from_db()

    baseline_costs: dict[str, float] = {}
    if baseline_db and Path(baseline_db).exists():
        baseline = Tracker(persist_path=Path(baseline_db))
        baseline._records = baseline.load_from_db()
        baseline_costs = baseline.cost_by_function()

    current_costs = current.cost_by_function()
    total_current = current.total_cost()
    total_baseline = sum(baseline_costs.values())

    # Build markdown job summary
    lines = ["## tokenspy LLM Cost Report\n"]
    if total_baseline:
        delta = total_current - total_baseline
        pct = (delta / total_baseline) * 100
        arrow = "▲" if delta > 0 else "▼"
        lines.append(
            f"**Total: ${total_current:.4f}** "
            f"({arrow}{abs(pct):.1f}% vs baseline ${total_baseline:.4f})\n"
        )
    else:
        lines.append(f"**Total: ${total_current:.4f}**\n")

    lines.append("| Function | Cost | vs Baseline |")
    lines.append("|---|---|---|")

    regressions = []
    for fn, cost in sorted(current_costs.items(), key=lambda x: -x[1]):
        b = baseline_costs.get(fn, 0.0)
        if b:
            delta = cost - b
            pct = (delta / b) * 100
            vs = f"{'▲' if delta > 0 else '▼'}{abs(pct):.1f}%"
            if delta > 0 and pct > 10:
                regressions.append((fn, cost, b, delta, pct))
        else:
            vs = "new"
        lines.append(f"| `{fn}` | ${cost:.4f} | {vs} |")

    summary = "\n".join(lines)
    _write_step_summary(summary)
    print(summary)

    # Emit GHA annotations for regressions
    if _is_github_actions():
        for fn, cost, baseline_cost, delta, pct in regressions:
            _gha_annotate(
                "warning",
                "tokenspy cost regression",
                f"{fn}: cost increased by ${delta:.4f} ({pct:.1f}%) — "
                f"was ${baseline_cost:.4f}, now ${cost:.4f}",
            )
        if not regressions and baseline_costs:
            _gha_annotate("notice", "tokenspy", f"No cost regressions. Total: ${total_current:.4f}")


def compare_commits(db_path: str, commit1: str, commit2: str) -> None:
    """Compare LLM costs between two git commits stored in the database.

    Args:
        db_path: Path to SQLite database with git_commit column populated.
        commit1: First git commit SHA (baseline).
        commit2: Second git commit SHA (current).
    """
    import sqlite3

    path = Path(db_path)
    if not path.exists():
        print(f"[tokenspy] No DB found at {db_path}")
        return

    try:
        conn = sqlite3.connect(str(path))
        rows = conn.execute(
            "SELECT function_name, cost_usd, git_commit FROM llm_calls "
            "WHERE git_commit IN (?, ?)",
            (commit1, commit2),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[tokenspy] DB error: {e}")
        return

    costs1: dict[str, float] = {}
    costs2: dict[str, float] = {}
    for fn, cost, commit in rows:
        if commit == commit1:
            costs1[fn] = costs1.get(fn, 0.0) + cost
        elif commit == commit2:
            costs2[fn] = costs2.get(fn, 0.0) + cost

    all_fns = sorted(set(costs1) | set(costs2))
    print(f"\ntokenspy — cost comparison: {commit1} vs {commit2}")
    print(f"{'Function':<30} {commit1[:8]:>10} {commit2[:8]:>10} {'Delta':>10} {'Change':>8}")
    print("-" * 76)
    for fn in all_fns:
        c1 = costs1.get(fn, 0.0)
        c2 = costs2.get(fn, 0.0)
        delta = c2 - c1
        pct = ((delta / c1) * 100) if c1 > 0 else float("inf")
        arrow = "▲" if delta > 0 else "▼" if delta < 0 else "="
        pct_str = f"{pct:+.1f}%" if pct != float("inf") else "new"
        print(f"{fn:<30} ${c1:>9.4f} ${c2:>9.4f} {arrow}${abs(delta):>8.4f} {pct_str:>8}")
