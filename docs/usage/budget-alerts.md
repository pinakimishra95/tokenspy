# Budget Alerts

tokenspy can monitor cost per invocation and either warn or raise when a function exceeds its budget.

---

## Warning (default)

Set `budget_usd` on any decorated function:

```python
@tokenspy.profile(budget_usd=0.10)
def my_agent(query: str) -> str:
    ...
```

When a single invocation costs more than `$0.10`, Python emits a `UserWarning`:

```
UserWarning: [tokenspy] Budget exceeded in my_agent: $0.1423 > $0.1000
```

Execution continues normally — the warning is non-blocking.

---

## Raising an exception

Use `on_exceeded="raise"` to stop execution:

```python
@tokenspy.profile(budget_usd=0.10, on_exceeded="raise")
def strict_agent(query: str) -> str:
    ...
```

This raises `tokenspy.BudgetExceededError`:

```python
try:
    strict_agent(query)
except tokenspy.BudgetExceededError as e:
    print(f"Aborted: spent ${e.spent:.4f}, limit was ${e.budget:.4f}")
    # Handle gracefully — log, fallback, alert, etc.
```

---

## `BudgetExceededError`

| Attribute | Type | Description |
|---|---|---|
| `spent` | `float` | Actual cost of the invocation in USD |
| `budget` | `float` | Budget limit set on the decorator |

!!! info "Why `BaseException`?"
    `BudgetExceededError` inherits from `BaseException` (not `Exception`) so it propagates correctly through provider try/except guards that catch broad exceptions. Standard `except Exception` blocks in your code won't accidentally swallow it.

---

## Per-function budgets

Different budgets for different functions:

```python
@tokenspy.profile(budget_usd=0.01)      # cheap function — tight budget
def classify(text: str) -> str:
    ...

@tokenspy.profile(budget_usd=1.00)      # expensive agent — loose budget
def deep_research(topic: str) -> str:
    ...
```

---

## Production use

Budget alerts are useful for:

- **Catching prompt injection** — an adversarial prompt that causes runaway token usage will trip the budget
- **Cost-safe multi-tenant apps** — per-request budget caps
- **Development guards** — fail fast if a refactor accidentally inflates costs

```python
@tokenspy.profile(budget_usd=0.05, on_exceeded="raise")
def process_user_request(user_input: str) -> str:
    # If this somehow costs more than $0.05, raise immediately
    ...
```
