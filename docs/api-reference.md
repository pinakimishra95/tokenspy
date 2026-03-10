# API Reference

Complete reference for all public symbols in tokenspy.

---

## Core API

### `tokenspy.profile`

```python
@tokenspy.profile
def my_function(): ...

@tokenspy.profile(budget_usd=0.10, on_exceeded="raise")
def strict_function(): ...
```

Decorator that intercepts all LLM calls made inside the decorated function.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `budget_usd` | `float \| None` | `None` | Max cost per invocation in USD. Triggers alert if exceeded. |
| `on_exceeded` | `"warn" \| "raise"` | `"warn"` | Action when budget is exceeded. |

Can be used with or without parentheses. Works on sync and async functions.

---

### `tokenspy.session()`

```python
with tokenspy.session(name="my_session") as s:
    ...
```

Context manager that profiles all LLM calls within the `with` block. Returns a [`Session`](#session) object.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | `"session"` | Label for this session in reports |

---

### `tokenspy.report()`

```python
tokenspy.report()
tokenspy.report(format="html")
tokenspy.report(format="html", output="/tmp/report.html")
```

Render the cost report from the global tracker.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `format` | `"text" \| "html"` | `"text"` | Output format |
| `output` | `str \| None` | `None` | Output file path (HTML only). Default: `tokenspy_report.html` |

---

### `tokenspy.stats()`

```python
data = tokenspy.stats()
```

Return a dict with the full cost breakdown. See [Programmatic Access →](usage/programmatic.md) for the schema.

**Returns:** `dict[str, Any]`

---

### `tokenspy.reset()`

```python
tokenspy.reset()
```

Clear all recorded calls from the global in-memory tracker. Does not affect the SQLite database.

---

### `tokenspy.init()`

```python
tokenspy.init(persist=True, persist_dir="~/.tokenspy", track_git=True)
```

Configure tokenspy global state. Call once at app startup.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `persist` | `bool` | `False` | If `True`, save all calls to SQLite |
| `persist_dir` | `str \| None` | `None` | Directory for `usage.db`. Default: `~/.tokenspy/` |
| `track_git` | `bool` | `False` | If `True`, tag each call with current git commit SHA |

---

## `Session`

```python
with tokenspy.session("my_session") as s:
    ...
```

A profiling session returned by `tokenspy.session()`.

### Properties

| Property | Type | Description |
|---|---|---|
| `cost` | `float` | Total cost in USD |
| `cost_str` | `str` | Formatted cost string, e.g. `"$0.0042"` |
| `tokens` | `int` | Total tokens (input + output) |
| `calls` | `int` | Number of LLM API calls |

### Methods

#### `summary()`

```python
data = s.summary()
```

Returns the same structure as `tokenspy.stats()`.

---

## `BudgetExceededError`

Raised when `on_exceeded="raise"` and the function's cost exceeds `budget_usd`.

```python
try:
    strict_function()
except tokenspy.BudgetExceededError as e:
    print(e.spent)    # float — actual cost
    print(e.budget)   # float — budget limit
```

| Attribute | Type | Description |
|---|---|---|
| `spent` | `float` | Actual cost of the invocation |
| `budget` | `float` | Budget limit that was exceeded |

Inherits from `BaseException`.

---

## `Tracker`

Low-level accumulator for `CallRecord` objects. Usually accessed via `get_global_tracker()`.

```python
from tokenspy.tracker import Tracker, get_global_tracker

tracker = get_global_tracker()
```

### Constructor

```python
Tracker(persist_path: Path | None = None)
```

### Methods

| Method | Returns | Description |
|---|---|---|
| `record(rec)` | `None` | Add a `CallRecord` |
| `records()` | `list[CallRecord]` | All recorded calls |
| `reset()` | `None` | Clear all records |
| `total_cost()` | `float` | Sum of all `cost_usd` |
| `total_tokens()` | `int` | Sum of all `total_tokens` |
| `total_calls()` | `int` | Number of records |
| `cost_by_function()` | `dict[str, float]` | Cost per function, sorted desc |
| `cost_by_model()` | `dict[str, float]` | Cost per model, sorted desc |
| `summary()` | `dict` | Aggregated stats dict |
| `load_from_db()` | `list[CallRecord]` | Load records from SQLite |

### Module functions

| Function | Description |
|---|---|
| `get_global_tracker()` | Returns the default global `Tracker` |
| `set_global_tracker(tracker)` | Replace the global tracker |

---

## `CallRecord`

Dataclass representing one intercepted LLM API call.

| Field | Type | Description |
|---|---|---|
| `function_name` | `str` | Decorated function name |
| `model` | `str` | Model name |
| `provider` | `str` | `"openai"`, `"anthropic"`, `"google"`, `"langchain"`, `"unknown"` |
| `input_tokens` | `int` | Input token count |
| `output_tokens` | `int` | Output token count |
| `cost_usd` | `float` | Cost in USD |
| `duration_ms` | `float` | Latency in ms |
| `timestamp` | `float` | Unix timestamp |
| `session_id` | `str \| None` | Session name |
| `git_commit` | `str \| None` | Git SHA |
| `call_stack` | `list[str]` | Simplified call stack |
| `total_tokens` | `int` | `input_tokens + output_tokens` (property) |

---

## `TokenspyCallbackHandler`

LangChain / LangGraph callback handler.

```python
from tokenspy.integrations.langchain import TokenspyCallbackHandler

handler = TokenspyCallbackHandler()
handler = TokenspyCallbackHandler(tracker=my_tracker)  # custom tracker
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tracker` | `Tracker \| None` | `None` | Custom tracker. If `None`, uses global tracker. |

See [LangChain →](integrations/langchain.md) for usage examples.

---

## CI functions

```python
from tokenspy.ci import annotate_cost_diff, compare_commits
```

### `annotate_cost_diff(current_db, baseline_db=None)`

Compare costs between two databases and emit GitHub Actions annotations.

| Parameter | Type | Description |
|---|---|---|
| `current_db` | `str` | Path to current run's SQLite DB |
| `baseline_db` | `str \| None` | Path to baseline DB (optional) |

### `compare_commits(db_path, commit1, commit2)`

Compare costs between two git commits stored in the database.

| Parameter | Type | Description |
|---|---|---|
| `db_path` | `str` | SQLite database path |
| `commit1` | `str` | Baseline commit SHA |
| `commit2` | `str` | Current commit SHA |

---

## Pricing functions

```python
from tokenspy.pricing import calculate, get_price_per_million, list_models
```

| Function | Description |
|---|---|
| `calculate(model, input_tokens, output_tokens)` | Returns cost in USD |
| `get_price_per_million(model)` | Returns `(input_$/1M, output_$/1M)` or `None` |
| `get_cheaper_alternative(model)` | Returns cheaper model name or `None` |
| `list_models()` | Returns sorted list of all known models |
