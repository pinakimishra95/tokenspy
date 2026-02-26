"""
providers/openai.py — Intercepts OpenAI SDK calls.

Patches openai.resources.chat.completions.Completions.create (sync)
and the async variant. Falls back gracefully if openai is not installed.
Supports both streaming (stream=True) and non-streaming responses.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tokenspy.tracker import Tracker

_original_create: Any = None
_original_acreate: Any = None
_patched = False


class _OpenAIStreamWrapper:
    """Wraps an OpenAI streaming response to capture usage after iteration.

    OpenAI sends a final chunk with usage info when stream_options.include_usage=True.
    This wrapper passes all chunks through transparently and records after iteration.
    """

    def __init__(
        self,
        stream: Any,
        tracker: Tracker,
        current_function: list[str],
        kwargs: dict,
        start: float,
        provider: str,
    ) -> None:
        self._stream = stream
        self._tracker = tracker
        self._current_function = current_function
        self._kwargs = kwargs
        self._start = start
        self._provider = provider

    def __iter__(self) -> Any:
        last_chunk = None
        for chunk in self._stream:
            last_chunk = chunk
            yield chunk
        # After full iteration, record using the final chunk (contains usage)
        if last_chunk is not None:
            duration_ms = (time.perf_counter() - self._start) * 1000
            _record(self._tracker, self._current_function, last_chunk,
                    self._kwargs, duration_ms, self._provider)

    def __aiter__(self) -> Any:
        return self._async_iter()

    async def _async_iter(self) -> Any:
        last_chunk = None
        async for chunk in self._stream:
            last_chunk = chunk
            yield chunk
        if last_chunk is not None:
            duration_ms = (time.perf_counter() - self._start) * 1000
            _record(self._tracker, self._current_function, last_chunk,
                    self._kwargs, duration_ms, self._provider)

    def __enter__(self) -> _OpenAIStreamWrapper:
        if hasattr(self._stream, "__enter__"):
            self._stream.__enter__()
        return self

    def __exit__(self, *args: Any) -> Any:
        if hasattr(self._stream, "__exit__"):
            return self._stream.__exit__(*args)
        return None

    async def __aenter__(self) -> _OpenAIStreamWrapper:
        if hasattr(self._stream, "__aenter__"):
            await self._stream.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> Any:
        if hasattr(self._stream, "__aexit__"):
            return await self._stream.__aexit__(*args)
        return None


def patch(tracker: Tracker, current_function: list[str]) -> bool:
    """Monkey-patch the OpenAI SDK. Returns True if successful."""
    global _original_create, _original_acreate, _patched

    try:
        from openai.resources.chat.completions import Completions
    except ImportError:
        return False

    if _patched:
        return True


    _original_create = Completions.create

    def _patched_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        is_stream = kwargs.get("stream", False)
        if is_stream:
            # Inject stream_options to get usage in the final chunk
            kwargs.setdefault("stream_options", {})
            kwargs["stream_options"]["include_usage"] = True

        start = time.perf_counter()
        response = _original_create(self, *args, **kwargs)

        if is_stream:
            return _OpenAIStreamWrapper(response, tracker, current_function, kwargs, start, "openai")

        duration_ms = (time.perf_counter() - start) * 1000
        _record(tracker, current_function, response, kwargs, duration_ms, "openai")
        return response

    Completions.create = _patched_create  # type: ignore[method-assign]

    # Async variant (best-effort)
    try:
        from openai.resources.chat.completions import AsyncCompletions

        _original_acreate = AsyncCompletions.create

        async def _patched_acreate(self: Any, *args: Any, **kwargs: Any) -> Any:
            is_stream = kwargs.get("stream", False)
            if is_stream:
                kwargs.setdefault("stream_options", {})
                kwargs["stream_options"]["include_usage"] = True

            start = time.perf_counter()
            response = await _original_acreate(self, *args, **kwargs)

            if is_stream:
                return _OpenAIStreamWrapper(response, tracker, current_function, kwargs, start, "openai")

            duration_ms = (time.perf_counter() - start) * 1000
            _record(tracker, current_function, response, kwargs, duration_ms, "openai")
            return response

        AsyncCompletions.create = _patched_acreate  # type: ignore[method-assign]
    except Exception:
        pass

    _patched = True
    return True


def unpatch() -> None:
    global _original_create, _original_acreate, _patched

    if not _patched:
        return

    try:
        from openai.resources.chat.completions import Completions

        if _original_create is not None:
            Completions.create = _original_create  # type: ignore[method-assign]

        from openai.resources.chat.completions import AsyncCompletions

        if _original_acreate is not None:
            AsyncCompletions.create = _original_acreate  # type: ignore[method-assign]
    except Exception:
        pass

    _patched = False
    _original_create = None
    _original_acreate = None


def _record(
    tracker: Tracker,
    current_function: list[str],
    response: Any,
    kwargs: dict,
    duration_ms: float,
    provider: str,
) -> None:
    try:
        from tokenspy import pricing
        from tokenspy.tracker import CallRecord

        model = kwargs.get("model", "unknown")
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        cost = pricing.calculate(model, input_tokens, output_tokens)

        fn_name = current_function[0] if current_function else "<unknown>"
        tracker.record(
            CallRecord(
                function_name=fn_name,
                call_stack=list(current_function),
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
            )
        )
    except Exception:
        pass  # never crash user code
