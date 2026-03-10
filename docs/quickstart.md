# Quickstart

This walkthrough shows tokenspy on a realistic multi-function pipeline in under 3 minutes.

## The scenario

You have a pipeline with three functions that each make LLM calls. You want to know which one costs the most.

```python
import openai
import tokenspy

client = openai.OpenAI()

# (1) Decorate each function you want to profile
@tokenspy.profile
def fetch_and_summarize(query: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize recent news about: {query}"}]
    )
    return response.choices[0].message.content

@tokenspy.profile
def extract_entities(text: str) -> list[str]:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"List named entities in: {text}"}]
    )
    return response.choices[0].message.content.split("\n")

@tokenspy.profile
def generate_report(entities: list[str]) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Write a report on: {entities}"}]
    )
    return response.choices[0].message.content

# (2) Run your pipeline normally
docs = fetch_and_summarize("Q3 earnings")
entities = extract_entities(docs)
report = generate_report(entities)

# (3) See the cost breakdown
tokenspy.report()
```

## Output — terminal flame graph

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

**Result:** `fetch_and_summarize` burns 73% of the budget. Switching it to `gpt-4o-mini` saves ~$540/month.

---

## HTML report

For a richer visual:

```python
tokenspy.report(format="html")
# Writes tokenspy_report.html and opens it in your browser
```

---

## Programmatic access

Access the raw numbers from your code:

```python
data = tokenspy.stats()
print(data["total_cost_usd"])    # 0.0523
print(data["by_function"])       # {"fetch_and_summarize": 0.038, ...}
print(data["by_model"])          # {"gpt-4o": 0.049, "gpt-4o-mini": 0.003}
```

---

## What's next?

| Goal | Guide |
|---|---|
| Profile an async function | [Decorator →](usage/decorator.md) |
| Profile a block of code | [Context Manager →](usage/context-manager.md) |
| Set a cost budget | [Budget Alerts →](usage/budget-alerts.md) |
| Save history across runs | [Persistence →](usage/persistence.md) |
| Profile LangChain chains | [LangChain →](integrations/langchain.md) |
| Catch cost regressions in CI | [GitHub Actions →](integrations/github-actions.md) |
