# Programmatic Access

Beyond `report()`, tokenspy exposes its raw data so you can build dashboards, alerts, or custom reporting.

---

## `tokenspy.stats()`

Returns a complete snapshot of all recorded calls:

```python
data = tokenspy.stats()
```

### Return value

```python
{
    "total_cost_usd": 0.042,         # float — total cost across all calls
    "total_tokens": 15000,           # int   — total tokens (input + output)
    "total_calls": 3,                # int   — number of LLM API calls
    "by_function": {                 # dict  — cost by function, sorted by cost
        "fetch_and_summarize": 0.038,
        "generate_report": 0.004,
    },
    "by_model": {                    # dict  — cost by model, sorted by cost
        "gpt-4o": 0.040,
        "gpt-4o-mini": 0.002,
    },
    "calls": [                       # list  — individual call records (dicts)
        {
            "function_name": "fetch_and_summarize",
            "model": "gpt-4o",
            "provider": "openai",
            "input_tokens": 9000,
            "output_tokens": 3000,
            "cost_usd": 0.038,
            "duration_ms": 842.0,
            "timestamp": 1740556473.2,
            "session_id": None,
            "git_commit": None,
        },
        ...
    ]
}
```

---

## `tokenspy.reset()`

Clear all recorded calls from memory (does not affect the SQLite database):

```python
tokenspy.reset()
assert tokenspy.stats()["total_calls"] == 0
```

Useful when running experiments in sequence:

```python
# Experiment A
run_pipeline_v1()
stats_v1 = tokenspy.stats()
tokenspy.reset()

# Experiment B
run_pipeline_v2()
stats_v2 = tokenspy.stats()

print(f"v1 cost: ${stats_v1['total_cost_usd']:.4f}")
print(f"v2 cost: ${stats_v2['total_cost_usd']:.4f}")
```

---

## `CallRecord` fields

Each entry in `stats()["calls"]` maps to a `CallRecord` dataclass:

| Field | Type | Description |
|---|---|---|
| `function_name` | `str` | Decorated function that triggered the call |
| `model` | `str` | Model name (e.g. `"gpt-4o"`) |
| `provider` | `str` | `"openai"`, `"anthropic"`, `"google"`, `"langchain"`, `"unknown"` |
| `input_tokens` | `int` | Prompt token count |
| `output_tokens` | `int` | Completion token count |
| `cost_usd` | `float` | Cost in USD |
| `duration_ms` | `float` | End-to-end latency in milliseconds |
| `timestamp` | `float` | Unix timestamp of the call |
| `session_id` | `str \| None` | Session name if using `tokenspy.session()` |
| `git_commit` | `str \| None` | Git SHA if `track_git=True` |
| `total_tokens` | `int` | `input_tokens + output_tokens` (property) |

---

## Using the `Tracker` directly

For advanced use, access the global tracker:

```python
from tokenspy.tracker import get_global_tracker

tracker = get_global_tracker()

print(tracker.total_cost())          # float
print(tracker.total_tokens())        # int
print(tracker.total_calls())         # int
print(tracker.cost_by_function())    # dict[str, float]
print(tracker.cost_by_model())       # dict[str, float]

records = tracker.records()          # list[CallRecord]
for r in records:
    print(r.function_name, r.cost_usd, r.model)
```

### Replace the global tracker

Inject a custom tracker (e.g. with a specific DB path):

```python
from tokenspy.tracker import Tracker, set_global_tracker
from pathlib import Path

custom_tracker = Tracker(persist_path=Path("/tmp/test_run.db"))
set_global_tracker(custom_tracker)
```

---

## Build a cost alert

```python
import tokenspy

@tokenspy.profile
def my_pipeline(query):
    ...

my_pipeline(user_query)

data = tokenspy.stats()
if data["total_cost_usd"] > 1.00:
    send_slack_alert(f"High LLM cost: ${data['total_cost_usd']:.2f}")
```
