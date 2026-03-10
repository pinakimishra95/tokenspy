"""
eval/scorers.py — Built-in scorers for tokenspy evaluations.

A scorer is a callable with signature::

    scorer(output: str, expected: str) -> float  # returns 0.0–1.0

Or for llm_judge, returns a dict::

    {"score": float, "reasoning": str}

Built-in scorers:
    exact_match        — 1.0 if strings match exactly (after strip)
    contains           — 1.0 if expected is a substring of output
    levenshtein_sim    — normalized edit-distance similarity
    regex_match(pat)   — 1.0 if output matches regex pattern
    llm_judge(...)     — calls an LLM to rate the output (requires openai/anthropic)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

# ── Deterministic scorers ──────────────────────────────────────────────────────

def exact_match(output: str, expected: str) -> float:
    """Returns 1.0 if output exactly matches expected (after strip + lower)."""
    return 1.0 if str(output).strip().lower() == str(expected).strip().lower() else 0.0


exact_match.__name__ = "exact_match"


def contains(output: str, expected: str) -> float:
    """Returns 1.0 if expected is contained in output (case-insensitive)."""
    return 1.0 if str(expected).strip().lower() in str(output).lower() else 0.0


contains.__name__ = "contains"


def levenshtein_sim(output: str, expected: str) -> float:
    """Normalized Levenshtein similarity: 1.0 = identical, 0.0 = completely different."""
    a, b = str(output), str(expected)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    dist = dp[n]
    return 1.0 - dist / max(m, n)


levenshtein_sim.__name__ = "levenshtein_sim"


def regex_match(pattern: str, flags: int = re.IGNORECASE) -> Callable[[str, str], float]:
    """Factory: returns a scorer that checks if output matches the regex pattern.

    Example::

        scorer = regex_match(r"\\d{4}")   # matches if output contains a 4-digit number
    """
    compiled = re.compile(pattern, flags)

    def _scorer(output: str, expected: str) -> float:
        return 1.0 if compiled.search(str(output)) else 0.0

    _scorer.__name__ = f"regex({pattern!r})"
    return _scorer


# ── LLM-as-judge scorer ────────────────────────────────────────────────────────

def llm_judge(
    criteria: str = "quality and accuracy",
    model: str = "gpt-4o-mini",
    scale: tuple[float, float] = (0.0, 1.0),
    include_reasoning: bool = True,
) -> Callable:
    """Factory: returns a scorer that uses an LLM to rate the output.

    The returned scorer calls the LLM with a structured prompt and parses
    a JSON response with ``score`` and ``reasoning`` fields.

    Args:
        criteria: What to evaluate, e.g. "factual accuracy", "conciseness".
        model: LLM model to use for judging.
        scale: Score range. Default (0.0, 1.0) — normalised to [0, 1].
        include_reasoning: If True, returns a dict; if False, returns just the float.

    Example::

        scorer = llm_judge(criteria="factual accuracy", model="gpt-4o-mini")
        result = scorer("Paris is the capital of France.", "Paris")
        # {"score": 1.0, "reasoning": "Correct — Paris is indeed the capital."}
    """
    _PROMPT = """\
You are an evaluator. Rate the following AI output on the criterion: {criteria}.

Input (question/context): {input}
Expected output: {expected}
Actual output: {output}

Respond with ONLY a JSON object:
{{"score": <float between {min_score} and {max_score}>, "reasoning": "<one sentence>"}}
""".strip()

    def _scorer(output: str, expected: str, input: str = "") -> Any:
        prompt = _PROMPT.format(
            criteria=criteria,
            input=input or "(not provided)",
            expected=expected,
            output=output,
            min_score=scale[0],
            max_score=scale[1],
        )
        raw = _call_judge(model, prompt)
        try:
            import json
            data = json.loads(raw)
            score = float(data.get("score", scale[0]))
            # Normalise to [0, 1]
            lo, hi = scale
            norm_score = (score - lo) / (hi - lo) if hi != lo else 0.0
            if include_reasoning:
                return {"score": norm_score, "reasoning": data.get("reasoning", "")}
            return norm_score
        except Exception:
            return {"score": 0.0, "reasoning": f"Parse error: {raw[:100]}"} if include_reasoning else 0.0

    _scorer.__name__ = f"llm_judge({criteria!r})"
    return _scorer


def _call_judge(model: str, prompt: str) -> str:
    """Call an LLM and return the raw text response. Tries OpenAI then Anthropic."""
    try:
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        return response.choices[0].message.content or ""
    except ImportError:
        pass
    except Exception as e:
        return f'{{"score": 0.0, "reasoning": "OpenAI error: {e}"}}'

    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model if "claude" in model else "claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except ImportError:
        pass
    except Exception as e:
        return f'{{"score": 0.0, "reasoning": "Anthropic error: {e}"}}'

    return '{"score": 0.0, "reasoning": "No LLM provider available"}'
