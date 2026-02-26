"""
profiler.py — @profile decorator and session() context manager.

Usage:
    import tokenspy

    @tokenspy.profile
    def run_agent():
        ...

    @tokenspy.profile(budget_usd=0.10)
    def expensive_agent():
        ...  # warns if cost exceeds $0.10

    tokenspy.report()

    # Context manager
    with tokenspy.session() as s:
        ...
    print(s.cost)
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from tokenspy import interceptor as _interceptor
from tokenspy.tracker import CallRecord, Tracker, get_global_tracker, set_global_tracker

# ── Budget error ───────────────────────────────────────────────────────────────

class BudgetExceededError(BaseException):
    """Raised when a profiled function exceeds its cost budget (on_exceeded='raise').

    Inherits from BaseException (not Exception) so it propagates through
    ``except Exception: pass`` guards in the provider interceptors.
    """

    def __init__(self, spent: float, budget: float) -> None:
        self.spent = spent
        self.budget = budget
        super().__init__(
            f"tokenspy budget exceeded: spent ${spent:.4f} of ${budget:.4f} budget"
        )


# ── Decorator ──────────────────────────────────────────────────────────────────

def profile(
    func: Callable | None = None,
    *,
    budget_usd: float | None = None,
    on_exceeded: str = "warn",
) -> Any:
    """Decorator that intercepts all LLM calls made inside the function.

    Can be used with or without arguments::

        @tokenspy.profile
        def my_fn(): ...

        @tokenspy.profile()
        def my_fn(): ...

        @tokenspy.profile(budget_usd=0.10)
        def my_fn(): ...

        @tokenspy.profile(budget_usd=0.10, on_exceeded="raise")
        def my_fn(): ...

    Args:
        budget_usd: Maximum allowed cost per invocation in USD.
            If exceeded, triggers ``on_exceeded`` action.
        on_exceeded: What to do when budget is exceeded.
            ``"warn"`` (default) emits a warning.
            ``"raise"`` raises :class:`BudgetExceededError`.
    """
    if func is not None:
        # Used as @tokenspy.profile (no parens) — backward-compatible
        return _make_wrapper(func)
    # Used as @tokenspy.profile() or @tokenspy.profile(budget_usd=0.10)
    return lambda f: _make_wrapper(f, budget_usd=budget_usd, on_exceeded=on_exceeded)


def _make_wrapper(
    func: Callable,
    budget_usd: float | None = None,
    on_exceeded: str = "warn",
) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Ensure interceptors are active
        _interceptor.activate(get_global_tracker())
        prev = _interceptor.get_current_function()
        _interceptor.set_current_function(func.__qualname__)

        # Set up budget guard if requested
        guard: Callable[[CallRecord], None] | None = None
        if budget_usd is not None:
            baseline = get_global_tracker().total_cost()

            def _budget_check(_rec: CallRecord) -> None:
                spent = get_global_tracker().total_cost() - baseline
                if spent > budget_usd:
                    msg = (
                        f"[tokenspy] Budget exceeded in {func.__qualname__}: "
                        f"${spent:.4f} > ${budget_usd:.4f}"
                    )
                    if on_exceeded == "raise":
                        raise BudgetExceededError(spent, budget_usd)
                    else:
                        warnings.warn(msg, stacklevel=4)

            guard = _budget_check
            get_global_tracker()._post_record_hooks.append(guard)

        try:
            return func(*args, **kwargs)
        finally:
            if guard is not None:
                try:
                    get_global_tracker()._post_record_hooks.remove(guard)
                except ValueError:
                    pass
            _interceptor.set_current_function(prev)

    return wrapper


# ── Context manager / session ──────────────────────────────────────────────────

class Session:
    """A profiling session. Tracks calls made within a ``with`` block."""

    def __init__(self, name: str = "session") -> None:
        self.name = name
        self._tracker = Tracker()
        self._records: list[CallRecord] = []

    def __enter__(self) -> Session:
        _interceptor.activate(self._tracker)
        _interceptor.set_current_function(self.name)
        return self

    def __exit__(self, *_: Any) -> None:
        self._records = self._tracker.records()
        _interceptor.deactivate()

    @property
    def cost(self) -> float:
        """Total cost in USD."""
        return self._tracker.total_cost() or sum(r.cost_usd for r in self._records)

    @property
    def cost_str(self) -> str:
        return f"${self.cost:.4f}"

    @property
    def tokens(self) -> int:
        return self._tracker.total_tokens() or sum(r.total_tokens for r in self._records)

    @property
    def calls(self) -> int:
        return len(self._records)

    def summary(self) -> dict:
        return self._tracker.summary()


@contextmanager
def session(name: str = "session") -> Generator[Session, None, None]:
    """Context manager that profiles all LLM calls within the block."""
    s = Session(name=name)
    with s:
        yield s


# ── Global init ────────────────────────────────────────────────────────────────

def init(
    persist: bool = False,
    persist_dir: str | None = None,
    track_git: bool = False,
) -> None:
    """Configure tokenspy global state.

    Args:
        persist: If True, all calls are persisted to a local SQLite database.
        persist_dir: Directory for the SQLite file. Defaults to ~/.tokenspy/.
        track_git: If True, tag each call with the current git commit SHA.
    """
    if persist:
        db_dir = Path(persist_dir) if persist_dir else Path.home() / ".tokenspy"
        db_path = db_dir / "usage.db"
        tracker = Tracker(persist_path=db_path)
    else:
        tracker = Tracker()

    if track_git:
        import subprocess

        try:
            sha = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            tracker._git_commit = sha
        except Exception:
            pass  # not a git repo or git not installed — silently skip

    set_global_tracker(tracker)
    _interceptor.activate(tracker)
