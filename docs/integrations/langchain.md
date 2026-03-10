# LangChain / LangGraph

tokenspy integrates with LangChain and LangGraph through a callback handler. No proxy, no SDK swap — just add `TokenspyCallbackHandler` to your existing callbacks.

---

## Install

```bash
pip install tokenspy[langchain]
```

This adds `langchain-core>=0.2.0` as a dependency.

---

## With a chain

Pass the handler in `config`:

```python
from tokenspy.integrations.langchain import TokenspyCallbackHandler
import tokenspy

handler = TokenspyCallbackHandler()

result = chain.invoke(
    {"input": "Summarize this document"},
    config={"callbacks": [handler]}
)

tokenspy.report()
```

---

## With a model at construction time

Attach once to the model — all invocations are tracked automatically:

```python
from langchain_openai import ChatOpenAI
from tokenspy.integrations.langchain import TokenspyCallbackHandler
import tokenspy

llm = ChatOpenAI(
    model="gpt-4o-mini",
    callbacks=[TokenspyCallbackHandler()]
)

# Every call through this model is tracked
response = llm.invoke("What is a transformer?")
another = llm.invoke("Explain attention heads")

tokenspy.report()
```

---

## With LangGraph agents

The same callback system works with LangGraph:

```python
from langgraph.graph import StateGraph
from tokenspy.integrations.langchain import TokenspyCallbackHandler
import tokenspy

# Build your graph normally
builder = StateGraph(...)
# ... define nodes and edges ...
graph = builder.compile()

# Run with tokenspy callback
result = graph.invoke(
    {"messages": [("user", "Research quantum computing")]},
    config={"callbacks": [TokenspyCallbackHandler()]}
)

tokenspy.report()
```

---

## Custom tracker

Pass a specific `Tracker` instance instead of the global one:

```python
from tokenspy.tracker import Tracker
from tokenspy.integrations.langchain import TokenspyCallbackHandler

my_tracker = Tracker()
handler = TokenspyCallbackHandler(tracker=my_tracker)

chain.invoke(prompt, config={"callbacks": [handler]})

print(my_tracker.total_cost())
```

---

## Supported providers

`TokenspyCallbackHandler` extracts token counts from LangChain's `LLMResult` using three strategies:

| Provider | Token source |
|---|---|
| OpenAI | `response.llm_output["token_usage"]` |
| Anthropic | `response.llm_output["usage"]` |
| Others | `generation.generation_info` |

If no token data is available, the call is recorded with 0 tokens and `$0.00` cost (rather than failing silently).

---

## Combining with `@tokenspy.profile`

You can wrap the LangChain call in a profiled function to get function-level attribution:

```python
@tokenspy.profile
def run_chain(query: str) -> str:
    return chain.invoke(
        {"input": query},
        config={"callbacks": [TokenspyCallbackHandler()]}
    )["output"]

run_chain("Summarize Q3 results")
tokenspy.report()
```
