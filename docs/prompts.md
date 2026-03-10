# Prompt Versioning

Track every version of every prompt. Know exactly which prompt version caused a cost spike or quality drop.

## Quick example

```python
import tokenspy

tokenspy.init(persist=True)

# Push a new version (auto-increments: 1, 2, 3...)
p = tokenspy.prompts.push(
    "summarizer",
    "Summarize the following text in {{style}} style, max {{max_words}} words:\n\n{{text}}"
)
print(p.version)   # 1

# Compile with variables
compiled = p.compile(
    style="concise",
    max_words=100,
    text="Long document about climate change..."
)
# → "Summarize the following text in concise style, max 100 words:\n\nLong document..."
```

## Pull versions

```python
p_latest = tokenspy.prompts.pull("summarizer")           # latest version
p_v1     = tokenspy.prompts.pull("summarizer", version=1)
p_prod   = tokenspy.prompts.pull("summarizer", label="production")
```

## Mark production

```python
# Mark v2 as the production version
tokenspy.prompts.set_production("summarizer", version=2)

# Pull production-tagged version
p = tokenspy.prompts.pull("summarizer", label="production")
```

## List all prompts

```python
tokenspy.prompts.list()
# [
#   {"name": "summarizer", "version": 1, "is_production": False, ...},
#   {"name": "summarizer", "version": 2, "is_production": True,  ...},
# ]
```

## Template syntax

Variables use `{{double_braces}}`:

```python
p = tokenspy.prompts.push("greeter", "Hello, {{name}}! You have {{count}} messages.")
compiled = p.compile(name="Alice", count=3)
# → "Hello, Alice! You have 3 messages."
```

If a variable is not provided, tokenspy warns but still returns the template:

```python
result = p.compile()
# UserWarning: [tokenspy] Prompt 'greeter' v1 has unset variables: ['name', 'count']
```

## Delete a version

```python
tokenspy.prompts.delete("summarizer", version=1)
```

## Why this matters

When you run an experiment, you know exactly which prompt version was active. When costs spike, you can compare v1 vs v2 content and see what changed — then correlate with experiment scores to find the best version.
