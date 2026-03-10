# Streaming

tokenspy fully supports streaming responses from all providers. No code changes are needed — streaming is intercepted transparently.

---

## OpenAI streaming

```python
import tokenspy

@tokenspy.profile
def stream_response(query: str):
    for chunk in openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": query}],
        stream=True
    ):
        print(chunk.choices[0].delta.content or "", end="", flush=True)
    print()  # newline after stream

stream_response("Explain transformers in 3 sentences")
tokenspy.report()   # tokens + cost captured after stream completes
```

Output prints in real-time, then:

```
╔══════════════════════════════════════════════════════╗
║  tokenspy cost report                                ║
║  total: $0.0008  ·  320 tokens  ·  1 call           ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  stream_response  $0.0008  ████████████████  100%   ║
║    └─ gpt-4o       $0.0008                           ║
║       └─ 320 tokens                                  ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## Anthropic streaming

```python
@tokenspy.profile
def stream_claude(query: str):
    with anthropic_client.messages.stream(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": query}],
        max_tokens=500,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()

stream_claude("Write a haiku about Python")
tokenspy.report()
```

---

## Async streaming

Works the same with async:

```python
@tokenspy.profile
async def async_stream(query: str):
    async with async_anthropic_client.messages.stream(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": query}],
        max_tokens=1024,
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
    print()
```

---

## How it works

When `stream=True`, the provider interceptor wraps the response iterator. It:

1. Lets chunks flow through to your code unchanged
2. Accumulates token counts from each chunk's `usage` field
3. Records the call to the tracker **after the stream is fully consumed**

!!! note
    Token counts for streaming responses are recorded when the stream ends — not at the start. This means `tokenspy.stats()` will reflect streaming calls only after the iterator is exhausted.
