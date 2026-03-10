# tokenspy

<div class="hero" markdown>

## You're spending $800/month on LLMs. Which function is burning it?

*Find out in one line. No proxy. No signup. No traffic rerouting.*

<div class="badges" markdown>
[![PyPI version](https://img.shields.io/pypi/v/tokenspy.svg)](https://pypi.org/project/tokenspy/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](https://pypi.org/project/tokenspy/)
</div>

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

=== "Decorator"

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

=== "Context Manager"

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

=== "LangChain"

    ```python
    from tokenspy.integrations.langchain import TokenspyCallbackHandler

    # Drop in — works with any chain or model
    chain.invoke(prompt, config={"callbacks": [TokenspyCallbackHandler()]})
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
╚══════════════════════════════════════════════════════════════════════╝
```

**Now you know: `fetch_and_summarize` is burning 73% of your budget. Fix that one function, cut your bill by $540/month.**

---

## Features

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
**:material-fire: Flame Graph**

Visual cost breakdown by function — instantly see which function is eating your budget.
</div>

<div class="feature-card" markdown>
**:material-shield-off: No Proxy**

Pure in-process monkey-patching. No traffic rerouting, no signup, no configuration.
</div>

<div class="feature-card" markdown>
**:material-lightning-bolt: Zero Dependencies**

Works with whatever SDK you already have. No extra packages required.
</div>

<div class="feature-card" markdown>
**:material-bell-alert: Budget Alerts**

Set per-function cost budgets. Warn or raise when exceeded.
</div>

<div class="feature-card" markdown>
**:material-database: Persistence**

SQLite storage across sessions. Tag calls with git commits. Query history via CLI.
</div>

<div class="feature-card" markdown>
**:material-github: GitHub Actions**

Cost diff per PR. Catch regressions before they merge. Native GHA annotations.
</div>

<div class="feature-card" markdown>
**:material-language-python: LangChain**

Drop-in callback handler for chains, models, and LangGraph agents.
</div>

<div class="feature-card" markdown>
**:material-stream: Streaming**

Fully supported. Token counts captured after stream completes — zero code changes.
</div>

</div>

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

## Next Steps

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
**[Installation →](getting-started.md)**

Get tokenspy installed and your first report in 2 minutes.
</div>

<div class="feature-card" markdown>
**[Quickstart →](quickstart.md)**

Full walkthrough with annotated output.
</div>

<div class="feature-card" markdown>
**[API Reference →](api-reference.md)**

Complete symbol table for every public function and class.
</div>

<div class="feature-card" markdown>
**[How It Works →](how-it-works.md)**

The monkey-patching architecture explained.
</div>

</div>
