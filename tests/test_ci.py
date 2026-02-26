"""Tests for GitHub Actions annotation and CI utilities."""

from __future__ import annotations

from pathlib import Path

from tokenspy.tracker import CallRecord, Tracker


def _write_db(path: Path, records: list[tuple]) -> None:
    """Write records as (function_name, cost_usd) to a temp DB."""
    t = Tracker(persist_path=path)
    for fn, cost in records:
        t.record(
            CallRecord(
                function_name=fn,
                call_stack=[fn],
                model="gpt-4o",
                input_tokens=100,
                output_tokens=50,
                cost_usd=cost,
                duration_ms=100.0,
                provider="openai",
            )
        )


class TestAnnotateCostDiff:
    def test_no_baseline_reports_totals(self, tmp_path, capsys):
        db = tmp_path / "current.db"
        _write_db(db, [("agent_run", 0.05), ("search", 0.02)])
        from tokenspy.ci import annotate_cost_diff

        annotate_cost_diff(str(db))
        out = capsys.readouterr().out
        assert "0.0700" in out or "0.07" in out
        assert "agent_run" in out

    def test_with_baseline_shows_diff(self, tmp_path, capsys):
        baseline = tmp_path / "baseline.db"
        current = tmp_path / "current.db"
        _write_db(baseline, [("agent_run", 0.05)])
        _write_db(current, [("agent_run", 0.08)])  # 60% increase
        from tokenspy.ci import annotate_cost_diff

        annotate_cost_diff(str(current), str(baseline))
        out = capsys.readouterr().out
        assert "agent_run" in out
        # Should show percentage change
        assert "%" in out

    def test_nonexistent_current_db(self, tmp_path, capsys):
        from tokenspy.ci import annotate_cost_diff

        annotate_cost_diff(str(tmp_path / "missing.db"))
        out = capsys.readouterr().out
        assert "No DB found" in out

    def test_gha_annotate_outputs_workflow_command(self, capsys):
        from tokenspy.ci import _gha_annotate

        _gha_annotate("warning", "tokenspy cost regression", "fn: cost +50%")
        out = capsys.readouterr().out
        assert "::warning" in out
        assert "tokenspy cost regression" in out

    def test_gha_annotate_escapes_newlines(self, capsys):
        from tokenspy.ci import _gha_annotate

        _gha_annotate("notice", "test", "line1\nline2")
        out = capsys.readouterr().out
        # The message body (after last ::) should have newlines escaped to %0A
        # Note: print() adds a trailing \n to the whole line — strip it first
        msg_body = out.split("::")[-1].rstrip("\n")
        assert "\n" not in msg_body
        assert "%0A" in out

    def test_write_step_summary_no_env(self, tmp_path, monkeypatch):
        """_write_step_summary does nothing when GITHUB_STEP_SUMMARY is not set."""
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        from tokenspy.ci import _write_step_summary

        _write_step_summary("test content")  # should not raise or write anything

    def test_write_step_summary_writes_file(self, tmp_path, monkeypatch):
        """_write_step_summary appends to GITHUB_STEP_SUMMARY file."""
        summary_file = tmp_path / "summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        from tokenspy.ci import _write_step_summary

        _write_step_summary("## tokenspy cost")
        assert summary_file.exists()
        assert "## tokenspy cost" in summary_file.read_text()


class TestCompareCommits:
    def test_compare_two_commits(self, tmp_path, capsys):
        db = tmp_path / "usage.db"
        t = Tracker(persist_path=db)
        for commit, cost in [("abc1234", 0.05), ("def5678", 0.08)]:
            rec = CallRecord(
                function_name="my_agent", call_stack=["my_agent"],
                model="gpt-4o", input_tokens=100, output_tokens=50,
                cost_usd=cost, duration_ms=100.0, provider="openai",
                git_commit=commit,
            )
            t._save_to_db(rec)

        from tokenspy.ci import compare_commits

        compare_commits(str(db), "abc1234", "def5678")
        out = capsys.readouterr().out
        assert "my_agent" in out
        assert "abc1234" in out or "abc1234"[:8] in out

    def test_compare_missing_db(self, tmp_path, capsys):
        from tokenspy.ci import compare_commits

        compare_commits(str(tmp_path / "missing.db"), "abc", "def")
        out = capsys.readouterr().out
        assert "No DB found" in out
