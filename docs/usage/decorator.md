# Decorator

`@tokenspy.profile` is the primary way to track LLM costs. Add it to any function that makes LLM API calls — tokenspy intercepts all calls made inside that function and attributes the cost to it.

---

## Basic usage

```python
import tokenspy

@tokenspy.profile
def summarize_docs(docs: list[str]) -> str:
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "\n".join(docs)}]
    ).choices[0].message.content

summarize_docs(my_docs)
tokenspy.report()
```

---

## With parentheses (no options)

Both forms are equivalent:

```python
@tokenspy.profile          # no parentheses
@tokenspy.profile()        # empty parentheses — identical behavior
```

---

## Budget alerts

Warn when a single invocation exceeds a cost threshold:

```python
@tokenspy.profile(budget_usd=0.10)
def my_agent(query):
    ...
```

When exceeded, Python emits a `UserWarning`:

```
UserWarning: [tokenspy] Budget exceeded in my_agent: $0.1423 > $0.1000
```

### Raise instead of warn

```python
@tokenspy.profile(budget_usd=0.10, on_exceeded="raise")
def strict_agent(query):
    ...
```

Raises `tokenspy.BudgetExceededError` which you can catch:

```python
try:
    strict_agent(query)
except tokenspy.BudgetExceededError as e:
    print(f"Too expensive: spent ${e.spent:.4f}, limit ${e.budget:.4f}")
```

---

## Async functions

Works identically with `async def`:

```python
@tokenspy.profile
async def async_summarize(text: str) -> str:
    response = await async_openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}]
    )
    return response.choices[0].message.content
```

---

## Nested functions

When a profiled function calls another profiled function, each is tracked separately. The outer function's cost includes all nested calls:

```python
@tokenspy.profile
def fetch_and_summarize(query):
    ...

@tokenspy.profile
def run_pipeline(query):
    summary = fetch_and_summarize(query)  # ← tracked under fetch_and_summarize
    ...

run_pipeline("topic")
tokenspy.report()
# Both run_pipeline and fetch_and_summarize appear in the report
```

---

## Multiple calls

If a profiled function is called multiple times, all calls are accumulated:

```python
@tokenspy.profile
def classify(text):
    ...

for item in my_items:
    classify(item)

tokenspy.report()  # shows total across all calls, with call count
```

---

## Reset between runs

Clear recorded data between experiments:

```python
tokenspy.reset()   # clears all recorded calls
```

---

## Parameter reference

| Parameter | Type | Default | Description |
|---|---|---|---|
| `budget_usd` | `float \| None` | `None` | Maximum allowed cost per invocation in USD |
| `on_exceeded` | `"warn" \| "raise"` | `"warn"` | Action when budget is exceeded |
