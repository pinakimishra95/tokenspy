# GitHub Actions — Cost Diff Per PR

Catch cost regressions in CI before they ship.

## Setup

```python
# In your test / CI script
from tokenspy.ci import annotate_cost_diff

annotate_cost_diff("current_run.db", "baseline.db")
```

This prints GitHub Actions annotation format:

```
::warning::fetch_and_summarize cost increased $0.031 (62.4%)
```

And a summary table visible in the PR:

| Function | Cost | vs Baseline |
|---|---|---|
| `fetch_and_summarize` | $0.0812 | ▲62.4% |
| `extract_entities` | $0.0031 | ▼2.1% |

## Full workflow example

```yaml
# .github/workflows/cost-check.yml
name: Cost regression check

on: [pull_request]

jobs:
  cost-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install tokenspy[openai]

      # Download baseline DB from main branch artifact
      - uses: actions/download-artifact@v4
        with:
          name: tokenspy-baseline
          path: baseline/
        continue-on-error: true

      # Run your LLM tests and record costs
      - run: python tests/run_llm_tests.py --db current.db
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # Annotate the PR
      - run: |
          python -c "
          from tokenspy.ci import annotate_cost_diff
          annotate_cost_diff('current.db', 'baseline/baseline.db')
          "

      # Save as new baseline for future PRs
      - uses: actions/upload-artifact@v4
        with:
          name: tokenspy-baseline
          path: current.db
```

## CLI usage

```bash
tokenspy compare --db before.db --db after.db
tokenspy annotate --current current.db --baseline baseline.db
```
