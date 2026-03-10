# How It Works

tokenspy uses the same technique as `py-spy` and `line_profiler`: **in-process monkey-patching**. No proxy server, no HTTP interception, no environment variables.

---

## Architecture

```
Your Code
    │
    ├── @tokenspy.profile ────────────────────────────── sets active function name
    │
    └── openai_client.chat.completions.create(...)
                │
                └── tokenspy interceptor (in-process monkey-patch)
                        ├── calls original SDK method
                        ├── reads response.usage (tokens)
                        ├── looks up cost in built-in pricing table
                        ├── records: function · model · tokens · cost · duration
                        └── returns response UNCHANGED to your code

tokenspy.report() → renders flame graph from recorded data
```

Your code runs **exactly as before**. tokenspy just watches and keeps score.

---

## Provider interceptors

Each supported SDK is patched at a specific method:

| Provider | Patched method |
|---|---|
| OpenAI | `openai.resources.chat.completions.Completions.create` |
| Anthropic | `anthropic.resources.messages.Messages.create` |
| Google | `google.generativeai.GenerativeModel.generate_content` |

The patch replaces the original method with a wrapper that:

1. **Delegates** — calls the original method and captures the response
2. **Reads usage** — extracts `input_tokens`, `output_tokens` from the response
3. **Calculates cost** — looks up the model in the built-in pricing table
4. **Records** — creates a `CallRecord` and stores it in the active `Tracker`
5. **Returns** — passes the original response back to your code unchanged

---

## Function attribution

When `@tokenspy.profile` wraps a function, it pushes the function name onto a thread-local stack before calling the function, and pops it after. The interceptors read from this stack to know which function to attribute the cost to.

```
Thread-local stack: []

Enter @profile("run_pipeline")
  Stack: ["run_pipeline"]

  LLM call → recorded as function_name="run_pipeline"

  Enter @profile("fetch_and_summarize")
    Stack: ["run_pipeline", "fetch_and_summarize"]

    LLM call → recorded as function_name="fetch_and_summarize"

  Exit @profile("fetch_and_summarize")
  Stack: ["run_pipeline"]

Exit @profile("run_pipeline")
Stack: []
```

---

## Streaming

For streaming responses, the interceptor wraps the response iterator:

```python
# Simplified
def patched_create(**kwargs):
    response = original_create(**kwargs)
    if kwargs.get("stream"):
        return _wrap_stream(response, tracker, function_name)
    else:
        _record(response, tracker, function_name)
        return response
```

The wrapper yields chunks unchanged and accumulates token counts. The call is recorded to the tracker **after the last chunk is consumed**.

---

## Thread safety

The `Tracker` uses a `threading.Lock` around all writes. This means:

- Multiple threads can make LLM calls concurrently
- Each call is recorded atomically
- Function attribution uses thread-local storage — two threads in different profiled functions don't interfere

---

## Activation lifecycle

Interceptors are activated automatically when `@tokenspy.profile` or `tokenspy.session()` is first called. They persist until the process exits.

```python
from tokenspy.interceptor import activate, deactivate, is_active

activate()      # patch all available SDKs
is_active()     # True
deactivate()    # restore all original methods
is_active()     # False
```

If an SDK isn't installed, its interceptor silently does nothing — no import errors.

---

## Error handling

All interception code is wrapped in try/except. If tokenspy encounters an unexpected response format (e.g. a new SDK version), it logs a warning and returns the original response untouched. Your code is never interrupted by tokenspy bugs.

---

## Built-in pricing table

Cost calculations use a static pricing table compiled from official provider pricing pages. No network calls are made — the table is bundled with the package.

```python
from tokenspy.pricing import PRICING

# PRICING maps model name → (input_$/1M_tokens, output_$/1M_tokens)
print(PRICING["gpt-4o"])        # (2.5, 10.0)
print(PRICING["claude-haiku-4-5"])  # (0.8, 4.0)
```

See `tokenspy/pricing.py` for the full table, or call `tokenspy.pricing.list_models()` to get all known models.
