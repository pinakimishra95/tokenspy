"""
tokenspy — LLM cost profiler.

Find out which function is burning your LLM budget in one line.

Usage::

    import tokenspy

    @tokenspy.profile
    def run_agent(query: str):
        response = openai_client.chat.completions.create(...)
        return response

    run_agent("Summarize this")
    tokenspy.report()

    # Context manager
    with tokenspy.session() as s:
        response = anthropic_client.messages.create(...)
    print(s.cost_str)   # "$0.003"
"""

from __future__ import annotations

__version__ = "0.1.1"
__all__ = [
    "profile",
    "session",
    "report",
    "stats",
    "reset",
    "init",
    "Session",
]

from pathlib import Path
from typing import Any

from tokenspy.profiler import Session, init, profile, session
from tokenspy.tracker import get_global_tracker


def report(format: str = "text", output: str | None = None) -> None:
    """Print or render the cost report.

    Args:
        format: ``"text"`` (default) prints to stdout.
                ``"html"`` writes ``tokenspy_report.html`` and opens in browser.
        output: Path to write the HTML file (only used when format="html").
    """
    from tokenspy import flamegraph, optimizer

    tracker = get_global_tracker()

    if format == "html":
        out_path = Path(output) if output else Path("tokenspy_report.html")
        flamegraph.open_html_report(tracker, output_path=out_path)
        print(f"tokenspy: HTML report written to {out_path.resolve()}")
        return

    # Text report
    text = flamegraph.render_text(tracker)
    print(text)

    hints = optimizer.generate_hints(tracker)
    if hints:
        print(optimizer.render_hints(hints))


def stats() -> dict[str, Any]:
    """Return a dict with cost, token, and call breakdown.

    Example::

        {
            "total_cost_usd": 0.042,
            "total_tokens": 15000,
            "total_calls": 3,
            "calls": [...],
            "by_function": {"run_agent": 0.04, ...},
            "by_model": {"gpt-4o": 0.04, ...},
        }
    """
    return get_global_tracker().summary()


def reset() -> None:
    """Clear all recorded calls from the global tracker."""
    get_global_tracker().reset()
