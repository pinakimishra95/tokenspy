"""
integrations/langchain.py — LangChain / LangGraph callback handler.

Usage::

    from tokenspy.integrations.langchain import TokenspyCallbackHandler

    # With any LangChain chain or agent
    chain.invoke(prompt, config={"callbacks": [TokenspyCallbackHandler()]})

    # Or pass at construction time
    llm = ChatOpenAI(callbacks=[TokenspyCallbackHandler()])

    # With a custom tracker
    my_tracker = tokenspy.Tracker()
    handler = TokenspyCallbackHandler(tracker=my_tracker)

LangGraph uses the same LangChain callback system — no extra code needed.
Requires: pip install tokenspy[langchain]
"""

from __future__ import annotations

import time
from typing import Any

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.outputs import LLMResult

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    # Graceful fallback — provide a stub so imports don't fail
    BaseCallbackHandler = object  # type: ignore[misc,assignment]
    LLMResult = Any  # type: ignore[misc,assignment]
    _LANGCHAIN_AVAILABLE = False

from tokenspy import interceptor as _interceptor
from tokenspy import pricing
from tokenspy.tracker import CallRecord, Tracker, get_global_tracker


class TokenspyCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """LangChain callback handler that records LLM token costs to tokenspy.

    Records each LLM call (on_llm_end) to the tokenspy global tracker (or a
    custom tracker). Works with LangChain ChatModels, LLMs, and LangGraph agents.

    Token extraction supports:
    - OpenAI: ``llm_output["token_usage"]["prompt_tokens"/"completion_tokens"]``
    - Anthropic: ``llm_output["usage"]["input_tokens"/"output_tokens"]``
    - Others: falls back to 0 tokens with unknown model
    """

    def __init__(self, tracker: Tracker | None = None) -> None:
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-core is required. Install it with: pip install tokenspy[langchain]"
            )
        super().__init__()
        self._tracker = tracker or get_global_tracker()
        self._start: float | None = None
        self._fn_name: str = "<unknown>"

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        self._start = time.perf_counter()
        self._fn_name = _interceptor.get_current_function()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if self._start is None:
            return
        duration_ms = (time.perf_counter() - self._start) * 1000

        # Extract model name from various locations LangChain may populate it
        model = "unknown"
        llm_output = getattr(response, "llm_output", None) or {}
        if llm_output:
            model = (
                llm_output.get("model_name")
                or llm_output.get("model")
                or "unknown"
            )

        # Extract token usage — OpenAI uses "token_usage", Anthropic uses "usage"
        usage: dict = {}
        if llm_output:
            usage = llm_output.get("token_usage") or llm_output.get("usage") or {}

        input_tokens = int(
            usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        )
        output_tokens = int(
            usage.get("completion_tokens") or usage.get("output_tokens") or 0
        )
        cost = pricing.calculate(model, input_tokens, output_tokens)

        self._tracker.record(
            CallRecord(
                function_name=self._fn_name,
                call_stack=[self._fn_name],
                model=model,
                provider="langchain",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
            )
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        # Reset start time on error so we don't record a bad record
        self._start = None
