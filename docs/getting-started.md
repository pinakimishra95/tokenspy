# Installation

## Requirements

- Python **3.10+**
- Any of: `openai>=1.0`, `anthropic>=0.30`, `google-generativeai>=0.7`, or `langchain-core>=0.2`

tokenspy has **zero required dependencies** — it intercepts whatever SDK you already have installed.

---

## Install

```bash
pip install tokenspy
```

### Optional extras

Install alongside a specific provider:

```bash
# OpenAI
pip install tokenspy openai

# Anthropic
pip install tokenspy anthropic

# Google
pip install tokenspy google-generativeai

# LangChain / LangGraph
pip install tokenspy[langchain]

# Everything
pip install tokenspy[all]
```

---

## First Run

Add `@tokenspy.profile` to any function that makes LLM calls, then call `tokenspy.report()` at the end:

```python
import openai
import tokenspy

client = openai.OpenAI()

@tokenspy.profile
def summarize(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Summarize: {text}"]
    )
    return response.choices[0].message.content

result = summarize("Long document text here...")
tokenspy.report()
```

That's it. tokenspy intercepts the OpenAI call automatically and prints:

```
╔═══════════════════════════════════════════════╗
║  tokenspy cost report                         ║
║  total: $0.0003  ·  1,200 tokens  ·  1 call  ║
╠═══════════════════════════════════════════════╣
║                                               ║
║  summarize   $0.0003  ████████████████  100% ║
║    └─ gpt-4o-mini   $0.0003               ║
║       └─ 1,200 tokens                         ║
║                                               ║
╚═══════════════════════════════════════════════╝
```

---

## Next Steps

- [Quickstart →](quickstart.md) — a complete end-to-end example
- [Decorator →](usage/decorator.md) — all `@tokenspy.profile` options
- [Context Manager →](usage/context-manager.md) — scoped profiling with `tokenspy.session()`
