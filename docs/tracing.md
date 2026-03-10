# Structured Tracing

See *exactly* what happens inside every LLM call — inputs, outputs, tokens, latency — organized into a tree of spans, just like Langfuse. Everything stored locally.

## How it works

```
Your Code
    │
    ├── tokenspy.trace("research_pipeline")          ← top-level trace
    │       │
    │       ├── tokenspy.span("retrieve_docs")        ← child span
    │       │       └── vector_store.search(...)
    │       │
    │       ├── tokenspy.span("summarize", "llm")     ← LLM span
    │       │       └── client.chat.completions.create(...)
    │       │               │
    │       │               └── tokenspy interceptor auto-links:
    │       │                     model, input_tokens, output_tokens,
    │       │                     cost_usd, duration_ms → span record
    │       │
    │       └── tokenspy.span("rank_results")
    │
    └── t.score("relevance", 0.92)                   ← attach score
```

LLM calls made inside a span are **automatically linked** — no manual wiring.

## Code example

```python
import tokenspy

tokenspy.init(persist=True)   # save traces to ~/.tokenspy/usage.db

with tokenspy.trace("research_pipeline", input={"query": "climate change"}) as t:

    with tokenspy.span("retrieve_docs", span_type="retrieval") as s:
        docs = vector_store.search("climate change", top_k=5)
        s.update(output={"n_docs": len(docs), "sources": [d.title for d in docs]})

    with tokenspy.span("summarize", span_type="llm") as s:
        # Any LLM call here is AUTOMATICALLY attributed to this span
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Summarize: {docs}"}]
        )
        s.update(output=response.choices[0].message.content)

    with tokenspy.span("rank_results", span_type="function") as s:
        ranked = rerank(docs, response)
        s.update(output=ranked[:3])

    t.update(output=ranked[:3])

# Attach quality scores after the fact
t.score("relevance", 0.92, scorer="human")
t.score("hallucination", 0.05, scorer="llm_judge", comment="Grounded in sources")
```

## What gets recorded per span

```
Span: summarize
  ├── span_type:     llm
  ├── start_time:    2026-03-10 14:23:01.412
  ├── duration_ms:   842
  ├── model:         gpt-4o               ← auto-linked from LLM call
  ├── input_tokens:  4,200                ← auto-linked
  ├── output_tokens: 380                  ← auto-linked
  ├── cost_usd:      $0.0144              ← auto-linked
  ├── status:        ok
  └── output:        "Climate change refers to..."
```

## Nested spans and async

Works with nested spans and async code — no changes needed:

```python
async def run():
    async with tokenspy.trace("async_pipeline") as t:
        async with tokenspy.span("step1") as s:
            result = await async_llm_call()
            s.update(output=result)
```

## Why tracing matters

**Without tracing:**
```
cost report: run_pipeline → $0.052 total, 3 calls
```
You know the total. You don't know *which step* took 800ms or what the retrieval returned.

**With tracing:**
```
trace: research_pipeline  842ms  $0.052
  ├── retrieve_docs       12ms   $0.000  → returned 5 docs
  ├── summarize           810ms  $0.0144 → gpt-4o · 4,200 in · 380 out
  └── rank_results        8ms    $0.000  → [doc3, doc1, doc5]
  scores: relevance=0.92  hallucination=0.05
```
Full picture. Know exactly where time and money went. Inputs and outputs for debugging. Quality scores attached.

## Scores

```python
t.score("relevance", 0.92)
t.score("hallucination", 0.05, scorer="llm_judge", comment="Grounded in sources")
t.score("latency_ok", 1.0, scorer="code")
```

Score fields: `name`, `value` (0.0–1.0), `scorer` (`"human"` / `"llm_judge"` / `"code"`), `comment`.

## Viewing traces

```bash
tokenspy serve   # → http://localhost:7234 — Traces tab shows full span tree
```
