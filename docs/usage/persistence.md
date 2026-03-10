# Persistence

By default, tokenspy only tracks calls for the current process lifetime — data is lost when your program exits. Enable persistence to write every LLM call to a SQLite database so you can query history across sessions.

---

## Enable persistence

Call `tokenspy.init()` at the start of your app:

```python
import tokenspy

tokenspy.init(persist=True)
```

All subsequent calls are saved to `~/.tokenspy/usage.db`.

---

## Custom directory

```python
tokenspy.init(persist=True, persist_dir="/var/log/tokenspy")
# Saves to /var/log/tokenspy/usage.db
```

---

## Git commit tracking

Tag each call with the current git commit SHA:

```python
tokenspy.init(persist=True, track_git=True)
```

This lets you compare costs across commits — see [GitHub Actions →](../integrations/github-actions.md) and [CLI compare →](../cli.md).

---

## Full init example

```python
import tokenspy

# At app startup — call once
tokenspy.init(
    persist=True,                    # enable SQLite persistence
    persist_dir="~/.tokenspy",       # directory for usage.db (default)
    track_git=True,                  # tag calls with git SHA
)

@tokenspy.profile
def my_agent(query): ...

# Calls are now saved automatically
my_agent("Analyze this document")
```

---

## SQLite schema

The database table `llm_calls` has the following columns:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `function_name` | TEXT | Decorated function name |
| `call_stack` | TEXT | Simplified call stack (JSON) |
| `model` | TEXT | Model name (e.g. `gpt-4o`) |
| `provider` | TEXT | `openai`, `anthropic`, `google`, `langchain` |
| `input_tokens` | INTEGER | Input token count |
| `output_tokens` | INTEGER | Output token count |
| `cost_usd` | REAL | Cost in USD |
| `duration_ms` | REAL | Latency in milliseconds |
| `timestamp` | REAL | Unix timestamp |
| `session_id` | TEXT | Session name (if using `tokenspy.session()`) |
| `git_commit` | TEXT | Git commit SHA (if `track_git=True`) |

---

## Query directly with SQLite

```bash
sqlite3 ~/.tokenspy/usage.db "
  SELECT function_name, SUM(cost_usd), COUNT(*)
  FROM llm_calls
  WHERE date(timestamp, 'unixepoch') = date('now')
  GROUP BY function_name
  ORDER BY SUM(cost_usd) DESC;
"
```

---

## Load history programmatically

```python
from tokenspy.tracker import Tracker
from pathlib import Path

tracker = Tracker(persist_path=Path("~/.tokenspy/usage.db").expanduser())
records = tracker.load_from_db()

for r in records[:5]:
    print(f"{r.function_name}: ${r.cost_usd:.4f}  {r.model}")
```

---

## CLI access

Once persistence is enabled, inspect history from the terminal — see [CLI Reference →](../cli.md).

```bash
tokenspy history --limit 20
tokenspy report
```
