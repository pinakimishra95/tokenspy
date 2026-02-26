"""
cli.py — Command-line interface for tokenspy.

Commands:
    tokenspy history    Show recent LLM call history from the SQLite DB
    tokenspy report     Render a cost report (text or HTML)
    tokenspy compare    Diff costs between two databases or two git commits
    tokenspy annotate   Emit GitHub Actions cost annotations

Usage::

    tokenspy history --limit 20
    tokenspy report --format html
    tokenspy compare --db baseline.db --db current.db
    tokenspy compare --commit abc123 --commit def456 --db usage.db
    tokenspy annotate --current current.db --baseline baseline.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".tokenspy" / "usage.db"


def _load_tracker(db_path: str | None) -> Tracker:  # noqa: F821
    from tokenspy.tracker import Tracker

    path = Path(db_path) if db_path else DEFAULT_DB
    if not path.exists():
        print(
            f"[tokenspy] No database found at {path}\n"
            "  Run tokenspy.init(persist=True) in your code to enable persistence.",
            file=sys.stderr,
        )
        sys.exit(1)
    t = Tracker(persist_path=path)
    t._records = t.load_from_db()
    return t


# ── history ────────────────────────────────────────────────────────────────────

def cmd_history(args: argparse.Namespace) -> None:
    """Show recent LLM call history from the database."""
    import datetime

    tracker = _load_tracker(args.db)
    recs = tracker.records()[-args.limit :]

    if not recs:
        print("[tokenspy] No records found.")
        return

    header = f"{'Timestamp':<20} {'Function':<22} {'Model':<24} {'Cost':>10} {'Tokens':>8} {'ms':>8}"
    print(header)
    print("─" * len(header))
    for r in recs:
        ts = datetime.datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        fn = r.function_name[:21]
        model = r.model[:23]
        print(
            f"{ts:<20} {fn:<22} {model:<24} "
            f"${r.cost_usd:>9.4f} {r.total_tokens:>8} {r.duration_ms:>8.0f}"
        )
    print(f"\n  Total: {len(recs)} records | "
          f"${tracker.total_cost():.4f} | {tracker.total_tokens()} tokens")


# ── report ─────────────────────────────────────────────────────────────────────

def cmd_report(args: argparse.Namespace) -> None:
    """Render a cost report from the database."""
    from tokenspy import flamegraph, optimizer

    tracker = _load_tracker(args.db)

    if args.format == "html":
        out = Path(args.output) if args.output else Path("tokenspy_report.html")
        flamegraph.open_html_report(tracker, output_path=out)
        print(f"[tokenspy] HTML report written to {out.resolve()}")
    else:
        print(flamegraph.render_text(tracker))
        hints = optimizer.generate_hints(tracker)
        if hints:
            print(optimizer.render_hints(hints))


# ── compare ────────────────────────────────────────────────────────────────────

def cmd_compare(args: argparse.Namespace) -> None:
    """Compare costs across two databases or two git commits."""
    from tokenspy.tracker import Tracker

    # Git commit comparison mode
    if args.commit:
        if len(args.commit) != 2:
            print("[tokenspy] compare --commit requires exactly 2 SHA values", file=sys.stderr)
            sys.exit(1)
        from tokenspy.ci import compare_commits

        db = args.db[0] if args.db else str(DEFAULT_DB)
        compare_commits(db, args.commit[0], args.commit[1])
        return

    # DB diff mode
    if not args.db or len(args.db) != 2:
        print("[tokenspy] compare requires exactly 2 --db arguments", file=sys.stderr)
        sys.exit(1)

    trackers = []
    for db_path in args.db:
        t = Tracker(persist_path=Path(db_path))
        t._records = t.load_from_db()
        trackers.append(t)

    baseline_costs = trackers[0].cost_by_function()
    current_costs = trackers[1].cost_by_function()
    all_fns = sorted(set(baseline_costs) | set(current_costs))

    print(f"\ntokenspy — DB comparison: {args.db[0]} vs {args.db[1]}")
    header = f"{'Function':<30} {'Baseline':>12} {'Current':>12} {'Delta':>12} {'Change':>8}"
    print(header)
    print("─" * len(header))
    for fn in all_fns:
        b = baseline_costs.get(fn, 0.0)
        c = current_costs.get(fn, 0.0)
        delta = c - b
        pct = ((delta / b) * 100) if b > 0 else float("inf")
        arrow = "▲" if delta > 0 else "▼" if delta < 0 else "="
        pct_str = f"{pct:+.1f}%" if pct != float("inf") else "new"
        print(f"{fn:<30} ${b:>11.4f} ${c:>11.4f} {arrow}${abs(delta):>10.4f} {pct_str:>8}")


# ── annotate ───────────────────────────────────────────────────────────────────

def cmd_annotate(args: argparse.Namespace) -> None:
    """Emit GitHub Actions cost annotations."""
    from tokenspy.ci import annotate_cost_diff

    annotate_cost_diff(args.current, args.baseline)


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tokenspy",
        description="LLM cost profiler — find what's burning your AI budget",
    )
    parser.add_argument("--version", action="version", version=f"tokenspy {_version()}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # history
    h = sub.add_parser("history", help="Show recent LLM call history")
    h.add_argument("--limit", type=int, default=20, help="Max records to show (default: 20)")
    h.add_argument("--db", default=None, metavar="PATH", help="SQLite DB path")
    h.set_defaults(func=cmd_history)

    # report
    r = sub.add_parser("report", help="Render a cost report")
    r.add_argument("--format", choices=["text", "html"], default="text")
    r.add_argument("--db", default=None, metavar="PATH", help="SQLite DB path")
    r.add_argument("--output", default=None, metavar="FILE", help="Output file for HTML report")
    r.set_defaults(func=cmd_report)

    # compare
    c = sub.add_parser("compare", help="Compare costs across two DBs or git commits")
    c.add_argument("--db", action="append", metavar="PATH",
                   help="DB path (provide twice for DB comparison)")
    c.add_argument("--commit", action="append", metavar="SHA",
                   help="Git commit SHA (provide twice for commit comparison)")
    c.set_defaults(func=cmd_compare)

    # annotate
    a = sub.add_parser("annotate", help="Emit GitHub Actions cost annotations")
    a.add_argument("--current", required=True, metavar="PATH", help="Current run DB path")
    a.add_argument("--baseline", default=None, metavar="PATH", help="Baseline DB path")
    a.set_defaults(func=cmd_annotate)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)


def _version() -> str:
    try:
        from tokenspy import __version__

        return __version__
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
