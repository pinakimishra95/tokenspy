# Evaluations & Datasets

Run your LLM functions against golden test sets and track quality over time — like Braintrust, but local.

## Quick example

```python
import tokenspy
from tokenspy.eval import scorers

tokenspy.init(persist=True)

# 1. Build a dataset
ds = tokenspy.dataset("qa-golden")
ds.add(input={"question": "Capital of France?"}, expected_output="Paris")
ds.add(input={"question": "Capital of Germany?"}, expected_output="Berlin")
ds.from_json("more_test_cases.json")   # bulk import

# 2. Define the function under test
@tokenspy.profile
def answer_question(input: dict) -> str:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": input["question"]}]
    )
    return response.choices[0].message.content.strip()

# 3. Run the experiment
exp = tokenspy.experiment(
    "gpt4o-mini-baseline",
    dataset="qa-golden",
    fn=answer_question,
    scorers=[scorers.exact_match, scorers.contains],
)
results = exp.run()
results.summary()
```

**Terminal output:**

```
tokenspy — Experiment: gpt4o-mini-baseline
Dataset: qa-golden  (2 items)
────────────────────────────────────────────────────────
  ✓  Capital of France?     exact_match=1.0  contains=1.0  $0.0001  112ms
  ✓  Capital of Germany?    exact_match=1.0  contains=1.0  $0.0001   98ms
────────────────────────────────────────────────────────
  Passed:  2/2  (100.0%)
  Cost:    $0.0002
  Avg ms:  105
```

## Datasets

### Add items

```python
ds = tokenspy.dataset("my-dataset", description="QA pairs for v2 eval")

# Single item
ds.add(input={"q": "What is 2+2?"}, expected_output="4")

# Bulk from JSON
ds.from_json("test_cases.json")
# JSON format: [{"input": {...}, "expected_output": "..."}, ...]
```

### Load and export

```python
items = ds.items()     # list[DatasetItem]
len(ds)                # item count
ds.to_json("out.json") # export
```

## Built-in scorers

```python
from tokenspy.eval import scorers

scorers.exact_match(output, expected)        # 1.0 if exact, else 0.0
scorers.contains(output, expected)           # 1.0 if expected in output
scorers.levenshtein_similarity(output, expected)  # edit distance similarity

# Factory scorers
num_scorer = scorers.regex_match(r"\d+")    # returns 1.0 if pattern matches
```

## LLM-as-judge

```python
from tokenspy.eval import scorers

judge = scorers.llm_judge(
    criteria="Is the answer factually accurate and concise?",
    model="gpt-4o-mini",  # small model keeps eval costs low
)

exp = tokenspy.experiment(
    "accuracy-check",
    dataset="qa-golden",
    fn=answer_question,
    scorers=[scorers.exact_match, judge],
)
results = exp.run()
```

## Comparing experiments

After a prompt or model change, compare against the stored baseline:

```python
results.compare("gpt4o-mini-baseline")
```

```
Experiment comparison: gpt4o-mini-v2  vs  gpt4o-mini-baseline
────────────────────────────────────────────────
  exact_match:   0.95  →  0.80   ▼ 15%
  llm_judge:     0.88  →  0.91   ▲  3%
  cost:       $0.0002  →  $0.0003  ▲ 50%
  pass rate:    100%  →   80%    ▼ 20%
────────────────────────────────────────────────
```

## Exporting results

```python
results.to_json("results.json")
df = results.to_dataframe()   # requires pandas
```
