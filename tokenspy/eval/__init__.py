"""
tokenspy.eval — Evaluations and datasets.

Run your LLM functions against golden test sets, score them with
built-in or custom scorers, and compare runs over time.

Usage::

    import tokenspy
    from tokenspy.eval import scorers

    # Build a golden dataset
    ds = tokenspy.dataset("qa-golden")
    ds.add(input={"q": "Capital of France?"}, expected_output="Paris")
    ds.from_json("more_cases.json")

    # Run an experiment
    exp = tokenspy.experiment(
        name="gpt4o-mini-v1",
        dataset="qa-golden",
        fn=my_fn,
        scorers=[scorers.exact_match, scorers.llm_judge(criteria="accuracy")],
    )
    results = exp.run()
    results.summary()
    results.compare("gpt4o-v1")   # regression check vs previous run
"""

from tokenspy.eval import scorers
from tokenspy.eval.dataset import Dataset, DatasetItem
from tokenspy.eval.experiment import Experiment, ExperimentResults

__all__ = ["Dataset", "DatasetItem", "Experiment", "ExperimentResults", "scorers"]
