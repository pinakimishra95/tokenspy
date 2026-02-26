# llmspy 🔥

<div align="center">

**You're spending $800/month on LLMs. Which function is burning it?**

*Find out in one line. No proxy. No signup. No traffic rerouting.*

[![PyPI version](https://badge.fury.io/py/llmspy.svg)](https://badge.fury.io/py/llmspy)
[![Tests](https://github.com/pinakimishra95/llm-cost-profiler/actions/workflows/tests.yml/badge.svg)](https://github.com/pinakimishra95/llm-cost-profiler/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](https://pypi.org/project/llmspy/)

```bash
pip install llmspy
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

**llmspy takes 1 line. No proxy. No signup. Runs entirely on your machine.**

---

## The Fix

```python
import llmspy

@llmspy.profile
def run_pipeline(query):
    docs = fetch_and_summarize(query)
    entities = extract_entities(docs)
    return generate_report(entities)

run_pipeline("Analyze Q3 earnings")
llmspy.report()
```

---

## Output

```
╔══════════════════════════════════════════════════════════════════════╗
║  llmspy cost report                                                  ║
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
import llmspy

@llmspy.profile
def summarize_docs(docs: list[str]) -> str:
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "\n".join(docs)}]
    ).choices[0].message.content

summarize_docs(my_docs)
llmspy.report()            # prints flame graph to terminal
llmspy.report("html")     # writes llmspy_report.html, opens in browser
```

### Context Manager

```python
with llmspy.session("research_task") as s:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": query}]
    )

print(f"Cost:   {s.cost_str}")    # "$0.0012"
print(f"Tokens: {s.tokens}")      # 3,240
print(f"Calls:  {s.calls}")       # 1
```

### Programmatic Access

```python
data = llmspy.stats()
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
llmspy.init(persist=True)   # saves to ~/.llmspy/usage.db

# Decorate as normal — costs accumulate across restarts
@llmspy.profile
def my_agent(query):
    ...
```

---

## How It Works

llmspy monkey-patches the SDK client **in-process** — the same technique used by `py-spy` and `line_profiler`:

```
Your Code
    │
    ├── @llmspy.profile ────────────────────────────── sets active function
    │
    └── openai_client.chat.completions.create(...)
                │
                └── llmspy interceptor (in-process monkey-patch)
                        ├── calls original SDK method
                        ├── reads response.usage (tokens)
                        ├── looks up cost in built-in pricing table
                        ├── records: function · model · tokens · cost · duration
                        └── returns response UNCHANGED to your code

llmspy.report() → renders flame graph from recorded data
```

**No proxy server. No HTTP interception. No environment variables. No configuration.**

Your code runs exactly as before. llmspy just watches and keeps score.

---

## HTML Flame Graph

```python
llmspy.report(format="html")
```

Opens a self-contained HTML file in your browser — zero JS dependencies, pure SVG:

```
┌─────────────────────────────────────────────────────────────────┐
│  llmspy — Total: $0.0523  (18,734 tokens)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  fetch_and_summarize  ████████████████████████████████  73%     │
│  generate_report      ████████████                      21%     │
│  extract_entities     ████                               6%     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Model          │  Cost   │  %    │ Input  │ Output       │   │
│  │ gpt-4o         │ $0.049  │  94%  │ 15,600 │ 4,200        │   │
│  │ gpt-4o-mini    │ $0.003  │   6%  │  3,134 │    500       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Supported Providers

Automatically detected — nothing to configure:

| Provider | Package | Intercepted |
|---|---|---|
| **OpenAI** | `openai>=1.0` | `chat.completions.create` (sync + async) |
| **Anthropic** | `anthropic>=0.30` | `messages.create` (sync + async) |
| **Google** | `google-generativeai>=0.7` | `generate_content` |

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

[→ Full pricing table](llmspy/pricing.py)

---

## API Reference

| Symbol | Description |
|---|---|
| `@llmspy.profile` | Decorator — profile all LLM calls inside the function |
| `llmspy.session(name)` | Context manager — profile calls in a `with` block |
| `llmspy.report()` | Print text flame graph to terminal |
| `llmspy.report(format="html")` | Write + open HTML flame graph in browser |
| `llmspy.stats()` | Return full breakdown as a dict |
| `llmspy.reset()` | Clear all recorded calls |
| `llmspy.init(persist=True)` | Enable SQLite persistence across sessions |

---

## Comparison

| | Langfuse | Helicone | LiteLLM Proxy | **llmspy** |
|---|---|---|---|---|
| Requires proxy / gateway | ✅ yes | ✅ yes | ✅ yes | **❌ no** |
| Requires signup | ✅ yes | ✅ yes | ❌ no | **❌ no** |
| Local-first | ❌ no | ❌ no | ⚡ partial | **✅ yes** |
| Zero dependencies | ❌ no | ❌ no | ❌ no | **✅ yes** |
| Flame graph output | ❌ no | ❌ no | ❌ no | **✅ yes** |
| `@decorator` API | ❌ no | ❌ no | ❌ no | **✅ yes** |
| Optimization hints | ❌ no | ⚡ partial | ❌ no | **✅ yes** |
| Works offline | ❌ no | ❌ no | ⚡ partial | **✅ yes** |

---

## Roadmap

- [ ] Streaming response support (`stream=True`)
- [ ] Token budget alerts: `@llmspy.profile(budget_usd=0.10)`
- [ ] LangChain / LangGraph integration
- [ ] CLI: `llmspy history`, `llmspy report`
- [ ] GitHub Actions annotation (cost diff per PR)
- [ ] Cost comparison across git commits

---

## Contributing

```bash
git clone https://github.com/pinakimishra95/llm-cost-profiler
cd llm-cost-profiler
pip install -e ".[dev]"
pytest tests/                # 59 tests, ~0.1s
```

Issues and PRs welcome — especially for new provider support and updated pricing.

---

## License

MIT © [Pinaki Mishra](https://github.com/pinakimishra95). See [LICENSE](LICENSE).

---

<div align="center">

**Star this repo if you're tired of mystery LLM invoices.** ⭐

[GitHub](https://github.com/pinakimishra95/llm-cost-profiler) · [PyPI](https://pypi.org/project/llmspy/) · [Issues](https://github.com/pinakimishra95/llm-cost-profiler/issues)

</div>
