"""
eval/experiment.py — Experiment runner and results for tokenspy evaluations.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from tokenspy.eval.dataset import Dataset, DatasetItem, _get_db_path


@dataclass
class ExperimentResult:
    """Result for a single dataset item."""
    item: DatasetItem
    output: Any = None
    scores: dict[str, float] = field(default_factory=dict)
    passed: bool = False
    error: str | None = None
    cost_usd: float = 0.0
    duration_ms: float = 0.0


class ExperimentResults:
    """Aggregated results from an experiment run."""

    def __init__(self, experiment: Experiment, results: list[ExperimentResult]) -> None:
        self._experiment = experiment
        self._results = results

    def summary(self) -> None:
        """Print a results table to the terminal."""
        results = self._results
        if not results:
            print("[tokenspy] No results.")
            return

        scorer_names = list(results[0].scores.keys()) if results else []
        passed = sum(1 for r in results if r.passed)
        total_cost = sum(r.cost_usd for r in results)

        print(f"\ntokenspy experiment — {self._experiment.name}")
        print(f"Dataset: {self._experiment.dataset.name}  |  "
              f"{len(results)} items  |  "
              f"{passed}/{len(results)} passed  |  "
              f"${total_cost:.4f} total cost")

        # Header
        col_w = 30
        score_w = 12
        header = f"{'Input':<{col_w}} {'Output':<{col_w}}"
        for s in scorer_names:
            header += f" {s[:score_w-1]:>{score_w}}"
        header += f" {'Cost':>8}"
        print("\n" + header)
        print("─" * len(header))

        for r in results:
            if r.error:
                row = f"{'ERROR':>{col_w}} {r.error[:col_w-1]:<{col_w}}"
            else:
                inp = str(r.item.input)[:col_w - 1]
                out = str(r.output)[:col_w - 1]
                row = f"{inp:<{col_w}} {out:<{col_w}}"
                for s in scorer_names:
                    v = r.scores.get(s)
                    if isinstance(v, dict):
                        v = v.get("score", 0.0)
                    row += f" {v or 0.0:>{score_w}.2f}"
                row += f" ${r.cost_usd:>7.4f}"
            print(row)

        # Score averages
        if scorer_names:
            print("─" * len(header))
            avg_row = f"{'AVERAGE':<{col_w}} {'':<{col_w}}"
            for s in scorer_names:
                vals = []
                for r in results:
                    v = r.scores.get(s)
                    if isinstance(v, dict):
                        v = v.get("score")
                    if v is not None:
                        vals.append(float(v))
                avg = sum(vals) / len(vals) if vals else 0.0
                avg_row += f" {avg:>{score_w}.2f}"
            print(avg_row)

    def compare(self, name: str) -> None:
        """Compare scores against a previous experiment stored in the DB."""
        prev_results = _load_experiment_results(name)
        if not prev_results:
            print(f"[tokenspy] No experiment named {name!r} found in database.")
            return

        scorer_names = list(self._results[0].scores.keys()) if self._results else []
        print(f"\ntokenspy — Comparing {self._experiment.name!r} vs {name!r}")

        for s in scorer_names:
            curr_vals = [
                (r.scores.get(s) if not isinstance(r.scores.get(s), dict)
                 else r.scores[s].get("score", 0.0))
                for r in self._results if not r.error
            ]
            prev_vals = [
                (r["scores"].get(s) if not isinstance(r["scores"].get(s), dict)
                 else r["scores"][s].get("score", 0.0))
                for r in prev_results if not r.get("error")
            ]
            curr_avg = sum(v for v in curr_vals if v is not None) / max(len(curr_vals), 1)
            prev_avg = sum(v for v in prev_vals if v is not None) / max(len(prev_vals), 1)
            delta = curr_avg - prev_avg
            arrow = "▲" if delta > 0.01 else ("▼" if delta < -0.01 else "=")
            print(f"  {s:<30} {prev_avg:.3f} → {curr_avg:.3f}  {arrow}{abs(delta):.3f}")

    def to_json(self) -> dict:
        return {
            "experiment": self._experiment.name,
            "dataset": self._experiment.dataset.name,
            "results": [
                {
                    "input": r.item.input,
                    "expected": r.item.expected_output,
                    "output": r.output,
                    "scores": r.scores,
                    "passed": r.passed,
                    "error": r.error,
                    "cost_usd": r.cost_usd,
                    "duration_ms": r.duration_ms,
                }
                for r in self._results
            ],
        }

    def to_dataframe(self):  # type: ignore[return]
        """Return a pandas DataFrame (requires pandas)."""
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError("pip install pandas") from exc
        return pd.DataFrame([
            {
                "input": r.item.input,
                "expected": r.item.expected_output,
                "output": r.output,
                **r.scores,
                "cost_usd": r.cost_usd,
                "duration_ms": r.duration_ms,
                "error": r.error,
            }
            for r in self._results
        ])


class Experiment:
    """Runs a function against a dataset and scores the results.

    Usage::

        from tokenspy.eval import scorers

        exp = tokenspy.experiment(
            name="gpt4o-mini-baseline",
            dataset="qa-golden",
            fn=answer_fn,
            scorers=[scorers.exact_match, scorers.llm_judge()],
        )
        results = exp.run()
        results.summary()
    """

    def __init__(
        self,
        name: str,
        dataset: Dataset | str,
        fn: Callable,
        scorers: list[Callable],
    ) -> None:
        self.name = name
        self.dataset = dataset if isinstance(dataset, Dataset) else Dataset(dataset)
        self.fn = fn
        self.scorers = scorers
        self._id = str(uuid.uuid4())

    def run(self, pass_threshold: float = 0.5) -> ExperimentResults:
        """Run the function against all dataset items, score each output.

        Args:
            pass_threshold: Minimum average score to count a result as "passed".
        """
        from tokenspy.tracker import get_global_tracker

        items = self.dataset.items()
        results: list[ExperimentResult] = []

        for item in items:
            t0 = time.perf_counter()
            baseline_cost = get_global_tracker().total_cost()
            output = None
            error = None
            scores: dict[str, Any] = {}

            try:
                output = self.fn(item.input)
            except Exception as exc:
                error = str(exc)

            duration_ms = (time.perf_counter() - t0) * 1000
            cost_usd = get_global_tracker().total_cost() - baseline_cost

            if error is None:
                for scorer in self.scorers:
                    try:
                        raw = scorer(str(output), str(item.expected_output or ""))
                        scores[scorer.__name__] = raw
                    except Exception as e:
                        scores[scorer.__name__] = {"score": 0.0, "reasoning": str(e)}

            # Determine pass/fail
            numeric_scores = []
            for v in scores.values():
                if isinstance(v, dict):
                    numeric_scores.append(float(v.get("score", 0.0)))
                else:
                    numeric_scores.append(float(v))
            avg = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0.0
            passed = avg >= pass_threshold and error is None

            result = ExperimentResult(
                item=item,
                output=output,
                scores=scores,
                passed=passed,
                error=error,
                cost_usd=cost_usd,
                duration_ms=duration_ms,
            )
            results.append(result)

        exp_results = ExperimentResults(self, results)
        self._persist(exp_results)
        return exp_results

    def _persist(self, results: ExperimentResults) -> None:
        db_path = _get_db_path()
        if db_path is None or not db_path.exists():
            return
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                "INSERT OR REPLACE INTO experiments "
                "(id, name, dataset_id, function_name, created_at) VALUES (?,?,?,?,?)",
                (self._id, self.name, self.dataset._id,
                 getattr(self.fn, "__qualname__", str(self.fn)), time.time()),
            )
            for r in results._results:
                conn.execute(
                    "INSERT INTO experiment_results "
                    "(id, experiment_id, dataset_item_id, output, scores, passed, error, cost_usd, duration_ms) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), self._id, r.item.id,
                        json.dumps(r.output) if r.output is not None else None,
                        json.dumps(r.scores),
                        1 if r.passed else 0,
                        r.error,
                        r.cost_usd, r.duration_ms,
                    ),
                )
            conn.commit()
            conn.close()
        except Exception:
            pass


# ── Helper ─────────────────────────────────────────────────────────────────────

def _load_experiment_results(name: str) -> list[dict]:
    db_path = _get_db_path()
    if db_path is None or not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT id FROM experiments WHERE name = ? ORDER BY created_at DESC LIMIT 1",
            (name,),
        ).fetchone()
        if not row:
            conn.close()
            return []
        exp_id = row[0]
        rows = conn.execute(
            "SELECT output, scores, passed, error, cost_usd FROM experiment_results "
            "WHERE experiment_id = ?",
            (exp_id,),
        ).fetchall()
        conn.close()
        return [
            {
                "output": json.loads(r[0]) if r[0] else None,
                "scores": json.loads(r[1]) if r[1] else {},
                "passed": bool(r[2]),
                "error": r[3],
                "cost_usd": r[4],
            }
            for r in rows
        ]
    except Exception:
        return []
