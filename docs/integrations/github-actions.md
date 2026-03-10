# GitHub Actions — Cost Diff Per PR

tokenspy can catch LLM cost regressions before they merge. Add it to your CI pipeline to get automatic cost comparisons with GitHub Actions annotations and job summaries.

---

## How it works

1. Your test suite runs with `persist=True` → writes `current.db`
2. You store a `baseline.db` (from `main` branch) as an artifact or commit
3. `annotate_cost_diff()` compares the two → emits GHA annotations

---

## Setup

### 1. In your test script

```python
import tokenspy
from tokenspy.ci import annotate_cost_diff

# Enable persistence at the start of your test suite
tokenspy.init(persist=True, persist_dir="/tmp/tokenspy_ci", track_git=True)

# ... run your LLM-using code / tests ...

# At the end: emit annotations
annotate_cost_diff(
    current_db="/tmp/tokenspy_ci/usage.db",
    baseline_db="baseline.db",          # optional — omit for absolute-only report
)
```

### 2. GitHub Actions workflow

```yaml
name: LLM Cost Check

on:
  pull_request:
    branches: [main]

jobs:
  cost-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install tokenspy[all] pytest

      - name: Download baseline
        uses: actions/download-artifact@v4
        with:
          name: tokenspy-baseline
          path: .
        continue-on-error: true   # first run won't have a baseline yet

      - name: Run tests with cost tracking
        run: pytest tests/

      - name: Upload new baseline
        if: github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v4
        with:
          name: tokenspy-baseline
          path: /tmp/tokenspy_ci/usage.db
          retention-days: 90
```

---

## Annotations output

When a cost regression is detected (>10% increase), tokenspy emits a GitHub Actions warning:

```
::warning title=tokenspy cost regression::fetch_and_summarize: cost increased by $0.0312 (62.4%)
```

When all costs are within threshold:

```
::notice title=tokenspy::All function costs within acceptable range.
```

---

## Job summary table

tokenspy also writes a Markdown table to `$GITHUB_STEP_SUMMARY`:

| Function | Baseline | Current | Change |
|---|---|---|---|
| `fetch_and_summarize` | $0.050 | $0.081 | ▲62.4% |
| `extract_entities` | $0.032 | $0.031 | ▼2.1% |
| `generate_report` | $0.012 | $0.012 | — |

---

## Compare two git commits

After collecting calls with `track_git=True`, compare costs between any two commits:

```python
from tokenspy.ci import compare_commits

compare_commits(
    db_path="~/.tokenspy/usage.db",
    commit1="abc123",    # baseline commit
    commit2="def456",    # current commit
)
```

Or via CLI:

```bash
tokenspy compare --commit abc123 --commit def456 --db ~/.tokenspy/usage.db
```

---

## `annotate_cost_diff` reference

```python
from tokenspy.ci import annotate_cost_diff

annotate_cost_diff(
    current_db="path/to/current.db",   # required — current run DB
    baseline_db="path/to/baseline.db", # optional — omit for absolute-only report
)
```

| Parameter | Type | Description |
|---|---|---|
| `current_db` | `str` | Path to the current run's SQLite database |
| `baseline_db` | `str \| None` | Path to baseline database for comparison |
