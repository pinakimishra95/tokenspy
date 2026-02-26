# tokenspy 🔥

<div align="center">

**You're spending $800/month on LLMs. Which function is burning it?**

*Find out in one line. No proxy. No signup. No traffic rerouting.*

[![PyPI version](https://img.shields.io/pypi/v/tokenspy.svg)](https://pypi.org/project/tokenspy/)
[![Tests](https://github.com/pinakimishra95/tokenspy/actions/workflows/tests.yml/badge.svg)](https://github.com/pinakimishra95/tokenspy/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](https://pypi.org/project/tokenspy/)

```bash
pip install tokenspy
```

</div>

---

## The Problem

You get an OpenAI invoice. It says **$800 this month**. You have no idea which function caused it.

```python
def run_pipeline(query):
    docs = fetch_and_summarize(query)    # ← costs $600?
    entities = extract_entities(docs)   # ← or this one?
    return generate_report(entities)    # ← or this one?
```

Langfuse and Helicone force you to reroute traffic through their proxy. Sign up. Configure. Break your local setup.

**tokenspy takes 1 line. No proxy. No signup. Runs entirely on your machine.**

---

## The Fix

```python
import tokenspy

@tokenspy.profile
def run_pipeline(query):
    docs = fetch_and_summarize(query)
    entities = extract_entities(docs)
    return generate_report(entities)

run_pipeline("Analyze Q3 earnings")
tokenspy.report()
```

---

## Output

```
╔══════════════════════════════════════════════════════════════════════╗
║  tokenspy cost report                                                ║
║  total: $0.0523  ·  18,734 tokens  ·  3 calls                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  fetch_and_summarize      $0.038  ████████████░░░░  73%             ║
║    └─ gpt-4o               $0.038  ████████████░░░░  73%            ║
║       └─ 12,000 tokens                                               ║
║                                                                      ║
║  generate_report          $0.011  ████░░░░░░░░░░░░  21%            ║
║    └─ gpt-4o               $0.011  ████░░░░░░░░░░░░  21%            ║
║       └─ 3,600 tokens                                                ║
║                                                                      ║
║  extract_entities         $0.003  █░░░░░░░░░░░░░░░   6%            ║
║    └─ gpt-4o-mini          $0.003  █░░░░░░░░░░░░░░░   6%            ║
║       └─ 3,134 tokens                                                ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  Optimization hints                                                  ║
║                                                                      ║
║  🔴 fetch_and_summarize [gpt-4o]                                     ║
║     Switch to gpt-4o-mini — 94% cheaper  (~$540/month savings)      ║
║                                                                      ║
║  🟡 fetch_and_summarize [gpt-4o]                                     ║
║     Avg input: 12,000 tokens. Trim context or limit retrieval.       ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Now you know: `fetch_and_summarize` is burning 73% of your budget. Fix that one function, cut your bill by $540/month.**

---

## Quick Start

### Decorator (most common)

```python
import tokenspy

@tokenspy.profile
def summarize_docs(docs: list[str]) -> str:
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "\n".join(docs)}]
    ).choices[0].message.content

summarize_docs(my_docs)
tokenspy.report()           # prints flame graph to terminal
tokenspy.report("html")    # writes tokenspy_report.html, opens in browser
```

### Context Manager

```python
with tokenspy.session("research_task") as s:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": query}]
    )

print(f"Cost:   {s.cost_str}")    # "$0.0012"
print(f"Tokens: {s.tokens}")      # 3,240
print(f"Calls:  {s.calls}")       # 1
```

### Streaming (works automatically)

```python
@tokenspy.profile
def stream_response(query):
    # stream=True is fully supported — no changes needed
    for chunk in openai_client.chat.completions.create(
        model="gpt-4o", messages=[...], stream=True
    ):
        print(chunk.choices[0].delta.content or "", end="")

stream_response("Summarize this")
tokenspy.report()   # tokens + cost captured after stream completes
```

### Budget Alerts

```python
# Warn if a single invocation costs more than $0.10
@tokenspy.profile(budget_usd=0.10)
def my_agent(query): ...

# Raise an exception instead of just warning
@tokenspy.profile(budget_usd=0.10, on_exceeded="raise")
def strict_agent(query): ...
```

```
UserWarning: [tokenspy] Budget exceeded in my_agent: $0.1423 > $0.1000
```

### Programmatic Access

```python
data = tokenspy.stats()
# {
#   "total_cost_usd": 0.042,
#   "total_tokens": 15000,
#   "total_calls": 3,
#   "by_function": {"summarize_docs": 0.038, "generate_report": 0.004},
#   "by_model":    {"gpt-4o": 0.040, "gpt-4o-mini": 0.002},
#   "calls": [...],
# }
```

### Persistent Tracking Across Sessions

```python
# In your app startup:
tokenspy.init(persist=True)            # saves to ~/.tokenspy/usage.db
tokenspy.init(persist=True, track_git=True)  # also tags each call with git SHA

@tokenspy.profile
def my_agent(query): ...
```

---

## CLI

After running with `persist=True`, inspect your usage from the terminal:

```bash
# Show recent call history
tokenspy history --limit 20

# Print cost report from saved data
tokenspy report
tokenspy report --format html

# Diff two runs (e.g. before and after a refactor)
tokenspy compare --db before.db --db after.db

# Compare costs between two git commits
tokenspy compare --commit abc123 --commit def456 --db ~/.tokenspy/usage.db
```

```
Timestamp            Function               Model                      Cost   Tokens       ms
───────────────────────────────────────────────────────────────────────────────────────────────
2026-02-26 09:14:33  run_agent              gpt-4o                   $0.0523   18734      842
2026-02-26 09:14:41  summarize_docs         claude-haiku-4-5         $0.0012    3240      210
```

---

## LangChain / LangGraph

No proxy, no SDK swap — just add a callback:

```python
from tokenspy.integrations.langchain import TokenspyCallbackHandler

# With any chain
chain.invoke(prompt, config={"callbacks": [TokenspyCallbackHandler()]})

# At model construction time
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", callbacks=[TokenspyCallbackHandler()])

# Works with LangGraph agents too — same callback system
```

```bash
pip install tokenspy[langchain]
```

---

## GitHub Actions — Cost Diff Per PR

Catch cost regressions before they merge:

```python
# In your CI test script:
from tokenspy.ci import annotate_cost_diff
annotate_cost_diff("current_run.db", "baseline.db")
```

Outputs GitHub Actions annotations:
```
::warning title=tokenspy cost regression::fetch_and_summarize: cost increased by $0.0312 (62.4%)
```

And writes a Markdown table to the job summary:

| Function | Cost | vs Baseline |
|---|---|---|
| `fetch_and_summarize` | $0.0812 | ▲62.4% |
| `extract_entities` | $0.0031 | ▼2.1% |

---

## How It Works

tokenspy monkey-patches the SDK client **in-process** — the same technique used by `py-spy` and `line_profiler`:

```
Your Code
    │
    ├── @tokenspy.profile ────────────────────────────── sets active function
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

**No proxy server. No HTTP interception. No environment variables. No configuration.**

Your code runs exactly as before. tokenspy just watches and keeps score.

---

## Supported Providers

Automatically detected — nothing to configure:

| Provider | Package | Intercepted |
|---|---|---|
| **OpenAI** | `openai>=1.0` | `chat.completions.create` (sync + async + streaming) |
| **Anthropic** | `anthropic>=0.30` | `messages.create` (sync + async + streaming) |
| **Google** | `google-generativeai>=0.7` | `generate_content` |
| **LangChain** | `langchain-core>=0.2` | Callback handler (any model/provider) |

---

## Built-in Pricing Table

30+ models, updated Feb 2026. No API call needed.

| Model | Input $/1M | Output $/1M |
|---|---|---|
| claude-opus-4-6 | $15.00 | $75.00 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5 | $0.80 | $4.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| o1 | $15.00 | $60.00 |
| gemini-1.5-pro | $1.25 | $5.00 |
| gemini-1.5-flash | $0.075 | $0.30 |

[→ Full pricing table](tokenspy/pricing.py)

---

## API Reference

| Symbol | Description |
|---|---|
| `@tokenspy.profile` | Decorator — profile all LLM calls inside the function |
| `@tokenspy.profile(budget_usd=0.10)` | Decorator with cost budget alert |
| `@tokenspy.profile(budget_usd=0.10, on_exceeded="raise")` | Raise `BudgetExceededError` if exceeded |
| `tokenspy.session(name)` | Context manager — profile calls in a `with` block |
| `tokenspy.report()` | Print text flame graph to terminal |
| `tokenspy.report(format="html")` | Write + open HTML flame graph in browser |
| `tokenspy.stats()` | Return full breakdown as a dict |
| `tokenspy.reset()` | Clear all recorded calls |
| `tokenspy.init(persist=True)` | Enable SQLite persistence across sessions |
| `tokenspy.init(track_git=True)` | Tag each call with current git commit SHA |
| `TokenspyCallbackHandler` | LangChain/LangGraph callback handler |
| `tokenspy history` | CLI: show recent call history |
| `tokenspy report` | CLI: render cost report |
| `tokenspy compare` | CLI: diff two DBs or two git commits |
| `tokenspy annotate` | CLI: emit GitHub Actions cost annotations |

---

## Comparison

| | Langfuse | Helicone | LiteLLM Proxy | **tokenspy** |
|---|---|---|---|---|
| Requires proxy / gateway | ✅ yes | ✅ yes | ✅ yes | **❌ no** |
| Requires signup | ✅ yes | ✅ yes | ❌ no | **❌ no** |
| Local-first | ❌ no | ❌ no | ⚡ partial | **✅ yes** |
| Zero dependencies | ❌ no | ❌ no | ❌ no | **✅ yes** |
| Flame graph output | ❌ no | ❌ no | ❌ no | **✅ yes** |
| `@decorator` API | ❌ no | ❌ no | ❌ no | **✅ yes** |
| Streaming support | ✅ yes | ✅ yes | ✅ yes | **✅ yes** |
| Budget alerts | ⚡ partial | ⚡ partial | ❌ no | **✅ yes** |
| LangChain integration | ✅ yes | ✅ yes | ✅ yes | **✅ yes** |
| CLI history/report | ❌ no | ❌ no | ❌ no | **✅ yes** |
| GitHub Actions cost diff | ❌ no | ❌ no | ❌ no | **✅ yes** |
| Git commit cost tracking | ❌ no | ❌ no | ❌ no | **✅ yes** |
| Optimization hints | ❌ no | ⚡ partial | ❌ no | **✅ yes** |
| Works offline | ❌ no | ❌ no | ⚡ partial | **✅ yes** |

---

## Contributing

```bash
git clone https://github.com/pinakimishra95/tokenspy
cd tokenspy
pip install -e ".[dev]"
pytest tests/    # 100 tests, ~0.2s
```

Issues and PRs welcome — especially for new provider support and updated pricing.

---

## License

MIT © [Pinaki Mishra](https://github.com/pinakimishra95). See [LICENSE](LICENSE).

---

<div align="center">

**Star this repo if you're tired of mystery LLM invoices.** ⭐

[GitHub](https://github.com/pinakimishra95/tokenspy) · [PyPI](https://pypi.org/project/tokenspy/) · [Issues](https://github.com/pinakimishra95/tokenspy/issues)

</div>
