# Context Manager

`tokenspy.session()` is a context manager that profiles all LLM calls within a `with` block. Use it when you want to measure a specific block of code without decorating a function.

---

## Basic usage

```python
import tokenspy

with tokenspy.session("research_task") as s:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": query}]
    )

print(f"Cost:   {s.cost_str}")    # "$0.0012"
print(f"Tokens: {s.tokens}")      # 3,240
print(f"Calls:  {s.calls}")       # 1
```

---

## Session properties

After the `with` block exits, the `Session` object exposes:

| Property | Type | Example | Description |
|---|---|---|---|
| `cost` | `float` | `0.0012` | Total cost in USD |
| `cost_str` | `str` | `"$0.0012"` | Human-readable cost string |
| `tokens` | `int` | `3240` | Total tokens (input + output) |
| `calls` | `int` | `1` | Number of LLM API calls made |

---

## `summary()` method

Get the full breakdown as a dict:

```python
with tokenspy.session("pipeline") as s:
    ...

data = s.summary()
# {
#   "total_cost_usd": 0.042,
#   "total_tokens": 15000,
#   "total_calls": 3,
#   "by_function": {"pipeline": 0.042},
#   "by_model":    {"gpt-4o": 0.040, "gpt-4o-mini": 0.002},
#   "calls": [...],
# }
```

---

## Named sessions

The `name` argument labels the session in reports. Useful when running multiple sessions:

```python
with tokenspy.session("step_1_retrieval") as s1:
    retrieved = fetch_docs(query)

with tokenspy.session("step_2_synthesis") as s2:
    answer = synthesize(retrieved)

print(f"Retrieval: {s1.cost_str}")
print(f"Synthesis: {s2.cost_str}")
```

---

## Default name

The `name` argument is optional. It defaults to `"session"`:

```python
with tokenspy.session() as s:
    ...
```

---

## Combining with the decorator

Sessions and decorators work together. A session scopes its own tracker, while the decorator uses the global tracker:

```python
@tokenspy.profile
def summarize(text):
    ...

with tokenspy.session("experiment") as s:
    summarize(text)   # also recorded in the global tracker

print(s.cost_str)      # cost of calls made inside the with block
tokenspy.report()      # global report (includes all profiled calls)
```

---

## Accessing calls inside the block

You can access the session in real-time inside the block (though `cost` will be `0.0` until the call completes):

```python
with tokenspy.session("live") as s:
    response = client.chat.completions.create(...)
    # After this line, s.cost and s.tokens are populated
    print(s.cost_str)
```
