"""Tests for budget alerts: @tokenspy.profile(budget_usd=...)."""

from __future__ import annotations

import warnings

import pytest

from tokenspy.profiler import BudgetExceededError
from tokenspy.tracker import CallRecord, Tracker, get_global_tracker


def _make_fake_openai_call(tracker: Tracker, cost_usd: float = 0.05) -> None:
    """Directly inject a CallRecord as if an OpenAI call was made."""
    tracker.record(
        CallRecord(
            function_name="test_fn",
            call_stack=["test_fn"],
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=cost_usd,
            duration_ms=100.0,
            provider="openai",
        )
    )


class TestBudgetAlerts:
    def test_budget_no_exceed_no_warning(self):
        """Under-budget calls produce no warnings."""
        import tokenspy

        tokenspy.reset()

        @tokenspy.profile(budget_usd=1.00)
        def cheap_agent():
            _make_fake_openai_call(get_global_tracker(), cost_usd=0.01)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cheap_agent()
            assert not any("budget" in str(warning.message).lower() for warning in w)

    def test_budget_exceeded_emits_warning(self):
        """Exceeding budget emits a UserWarning."""
        import tokenspy

        tokenspy.reset()

        @tokenspy.profile(budget_usd=0.001)
        def expensive_agent():
            _make_fake_openai_call(get_global_tracker(), cost_usd=0.05)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            expensive_agent()
            budget_warnings = [x for x in w if "budget" in str(x.message).lower()]
            assert len(budget_warnings) >= 1

    def test_budget_exceeded_raises_on_raise_mode(self):
        """on_exceeded='raise' raises BudgetExceededError."""
        import tokenspy

        tokenspy.reset()

        @tokenspy.profile(budget_usd=0.001, on_exceeded="raise")
        def expensive_agent():
            _make_fake_openai_call(get_global_tracker(), cost_usd=0.05)

        with pytest.raises(BudgetExceededError) as exc_info:
            expensive_agent()
        assert exc_info.value.spent > 0.001
        assert exc_info.value.budget == 0.001

    def test_budget_error_attributes(self):
        """BudgetExceededError has .spent and .budget attributes."""
        err = BudgetExceededError(0.15, 0.10)
        assert err.spent == 0.15
        assert err.budget == 0.10
        assert "0.1500" in str(err)
        assert "0.1000" in str(err)

    def test_budget_guard_removed_after_function(self):
        """Budget guard hook is cleaned up after function returns."""
        import tokenspy

        tokenspy.reset()

        @tokenspy.profile(budget_usd=0.001)
        def my_fn():
            _make_fake_openai_call(get_global_tracker(), cost_usd=0.05)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            try:
                my_fn()
            except Exception:
                pass

        # After function returns, hooks should be cleared
        assert len(get_global_tracker()._post_record_hooks) == 0

    def test_budget_no_args_still_works(self):
        """@tokenspy.profile without args still works (backward compat)."""
        import tokenspy

        tokenspy.reset()

        @tokenspy.profile
        def my_fn():
            _make_fake_openai_call(get_global_tracker(), cost_usd=0.05)

        my_fn()
        assert get_global_tracker().total_calls() == 1

    def test_budget_empty_parens_still_works(self):
        """@tokenspy.profile() without args still works."""
        import tokenspy

        tokenspy.reset()

        @tokenspy.profile()
        def my_fn():
            _make_fake_openai_call(get_global_tracker(), cost_usd=0.05)

        my_fn()
        assert get_global_tracker().total_calls() == 1

    def test_post_record_hooks_called(self):
        """_post_record_hooks are called after each record."""
        tracker = Tracker()
        called_with = []
        tracker._post_record_hooks.append(lambda rec: called_with.append(rec))

        rec = CallRecord(
            function_name="fn", call_stack=["fn"], model="gpt-4o",
            input_tokens=10, output_tokens=5, cost_usd=0.01, duration_ms=50.0,
        )
        tracker.record(rec)
        assert len(called_with) == 1
        assert called_with[0] is rec

    def test_budget_exported_from_tokenspy(self):
        """BudgetExceededError is importable from tokenspy top-level."""
        from tokenspy import BudgetExceededError as BE

        assert BE is BudgetExceededError
