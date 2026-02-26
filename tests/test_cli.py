"""Tests for the tokenspy CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from tokenspy.tracker import CallRecord, Tracker


def _make_db_with_records(tmp_path: Path, n: int = 3) -> Path:
    """Create a temp SQLite DB with n fake call records."""
    db = tmp_path / "test.db"
    t = Tracker(persist_path=db)
    for i in range(n):
        t.record(
            CallRecord(
                function_name=f"fn_{i}",
                call_stack=[f"fn_{i}"],
                model="gpt-4o-mini",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                cost_usd=0.01 * (i + 1),
                duration_ms=50.0 * (i + 1),
                provider="openai",
            )
        )
    return db


class TestCLIHistory:
    def test_history_prints_records(self, tmp_path, capsys):
        db = _make_db_with_records(tmp_path, 3)
        import argparse

        from tokenspy.cli import cmd_history
        args = argparse.Namespace(limit=20, db=str(db))
        cmd_history(args)
        out = capsys.readouterr().out
        assert "fn_0" in out
        assert "fn_1" in out
        assert "fn_2" in out
        assert "gpt-4o-mini" in out

    def test_history_respects_limit(self, tmp_path, capsys):
        db = _make_db_with_records(tmp_path, 10)
        import argparse

        from tokenspy.cli import cmd_history
        args = argparse.Namespace(limit=2, db=str(db))
        cmd_history(args)
        out = capsys.readouterr().out
        # Only last 2 records should appear
        lines = [line for line in out.splitlines() if "fn_" in line]
        assert len(lines) == 2

    def test_history_no_db_exits(self, tmp_path):
        import argparse

        from tokenspy.cli import cmd_history
        args = argparse.Namespace(limit=20, db=str(tmp_path / "nonexistent.db"))
        with pytest.raises(SystemExit):
            cmd_history(args)


class TestCLIReport:
    def test_report_text_output(self, tmp_path, capsys):
        db = _make_db_with_records(tmp_path, 2)
        import argparse

        from tokenspy.cli import cmd_report
        args = argparse.Namespace(format="text", db=str(db), output=None)
        cmd_report(args)
        out = capsys.readouterr().out
        assert "tokenspy" in out.lower() or "$" in out

    def test_report_html_creates_file(self, tmp_path):
        db = _make_db_with_records(tmp_path, 2)
        out_file = tmp_path / "report.html"
        import argparse

        from tokenspy.cli import cmd_report
        args = argparse.Namespace(
            format="html", db=str(db), output=str(out_file)
        )
        # Patch webbrowser.open to avoid opening a browser in tests
        import unittest.mock
        with unittest.mock.patch("webbrowser.open"):
            cmd_report(args)
        assert out_file.exists()
        content = out_file.read_text()
        assert "<html" in content.lower()


class TestCLICompare:
    def test_compare_two_dbs(self, tmp_path, capsys):
        db1 = _make_db_with_records(tmp_path / "db1", 2)
        db2 = _make_db_with_records(tmp_path / "db2", 2)
        import argparse

        from tokenspy.cli import cmd_compare
        args = argparse.Namespace(db=[str(db1), str(db2)], commit=None)
        cmd_compare(args)
        out = capsys.readouterr().out
        assert "fn_" in out

    def test_compare_requires_two_dbs(self, tmp_path, capsys):
        db1 = _make_db_with_records(tmp_path, 2)
        import argparse

        from tokenspy.cli import cmd_compare
        args = argparse.Namespace(db=[str(db1)], commit=None)
        with pytest.raises(SystemExit):
            cmd_compare(args)

    def test_compare_commit_requires_two_shas(self, tmp_path, capsys):
        db = _make_db_with_records(tmp_path, 2)
        import argparse

        from tokenspy.cli import cmd_compare
        args = argparse.Namespace(db=[str(db)], commit=["abc123"])
        with pytest.raises(SystemExit):
            cmd_compare(args)


class TestCLIMain:
    def test_main_no_args_prints_help(self, capsys):
        import sys

        from tokenspy.cli import main

        old = sys.argv
        sys.argv = ["tokenspy"]
        try:
            main()
        finally:
            sys.argv = old
        out = capsys.readouterr().out
        assert "tokenspy" in out.lower()

    def test_main_version(self, capsys):
        import sys
        old = sys.argv
        sys.argv = ["tokenspy", "--version"]
        try:
            with pytest.raises(SystemExit):
                from tokenspy.cli import main
                main()
        finally:
            sys.argv = old
