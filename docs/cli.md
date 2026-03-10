# CLI Reference

The `tokenspy` CLI lets you inspect usage history, render reports, and compare costs across runs — all from the terminal.

!!! note "Requires persistence"
    CLI commands read from a SQLite database. Enable persistence in your app with `tokenspy.init(persist=True)` before using the CLI.

---

## `tokenspy history`

Show recent LLM call history.

```bash
tokenspy history
tokenspy history --limit 50
tokenspy history --db /path/to/custom.db
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--limit N` | `20` | Maximum number of records to show |
| `--db PATH` | `~/.tokenspy/usage.db` | Path to SQLite database |

**Example output:**

```
Timestamp            Function               Model                      Cost   Tokens       ms
───────────────────────────────────────────────────────────────────────────────────────────────
2026-02-26 09:14:33  run_agent              gpt-4o                   $0.0523   18734      842
2026-02-26 09:14:41  summarize_docs         claude-haiku-4-5         $0.0012    3240      210
2026-02-26 09:15:02  extract_entities       gpt-4o-mini              $0.0003     980       88
```

---

## `tokenspy report`

Render a cost report from saved data.

```bash
tokenspy report
tokenspy report --format html
tokenspy report --format html --output /tmp/my_report.html
tokenspy report --db /path/to/custom.db
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--format {text,html}` | `text` | Output format |
| `--output FILE` | `tokenspy_report.html` | Output file path (HTML only) |
| `--db PATH` | `~/.tokenspy/usage.db` | Path to SQLite database |

**Text output** — same flame graph as `tokenspy.report()` in Python.

**HTML output** — writes an interactive report and opens it in your default browser.

---

## `tokenspy compare`

Compare LLM costs across two databases or two git commits.

### Database mode

```bash
tokenspy compare --db before.db --db after.db
```

Pass `--db` twice — the first is the baseline, the second is current.

### Git commit mode

```bash
tokenspy compare --commit abc123 --commit def456
tokenspy compare --commit abc123 --commit def456 --db ~/.tokenspy/usage.db
```

Pass `--commit` twice — the first is the baseline commit, the second is current.

**Options:**

| Flag | Description |
|---|---|
| `--db PATH` | Database path (provide once for git mode, twice for db mode) |
| `--commit SHA` | Git commit SHA (provide twice) |

**Example output:**

```
Function               Baseline        Current         Change
────────────────────────────────────────────────────────────
fetch_and_summarize    $0.050          $0.081          ▲62.4%
extract_entities       $0.032          $0.031          ▼2.1%
generate_report        $0.012          $0.012          —
────────────────────────────────────────────────────────────
TOTAL                  $0.094          $0.124          ▲31.9%
```

---

## `tokenspy annotate`

Emit GitHub Actions cost annotations. Typically called from CI scripts.

```bash
tokenspy annotate --current /tmp/current.db
tokenspy annotate --current /tmp/current.db --baseline baseline.db
```

**Options:**

| Flag | Required | Description |
|---|---|---|
| `--current PATH` | Yes | Current run's database |
| `--baseline PATH` | No | Baseline database for comparison |

Outputs:
- `::warning` annotations for regressions (>10% increase)
- `::notice` annotation if all costs are within threshold
- Markdown table to `$GITHUB_STEP_SUMMARY`

See [GitHub Actions →](integrations/github-actions.md) for the full CI workflow.

---

## `tokenspy --version`

```bash
tokenspy --version
# tokenspy 0.1.3
```
