"""
providers/anthropic.py — Intercepts Anthropic SDK calls.

Patches anthropic.resources.messages.Messages.create (sync)
and the async variant. Falls back gracefully if anthropic is not installed.
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


class _AnthropicStreamWrapper:
    """Wraps an Anthropic streaming response to capture token usage from events.

    Anthropic streams typed events:
      - message_start: has message.usage.input_tokens
      - message_delta: has usage.output_tokens (cumulative)
      - message_stop: signals end of stream
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
        self._input_tokens = 0
        self._output_tokens = 0
        self._recorded = False

    def __iter__(self) -> Any:
        for event in self._stream:
            self._process_event(event)
            yield event
        self._finalize()

    def _process_event(self, event: Any) -> None:
        event_type = getattr(event, "type", None)
        if event_type == "message_start":
            msg = getattr(event, "message", None)
            if msg:
                usage = getattr(msg, "usage", None)
                if usage:
                    self._input_tokens = getattr(usage, "input_tokens", 0) or 0
        elif event_type == "message_delta":
            usage = getattr(event, "usage", None)
            if usage:
                self._output_tokens = getattr(usage, "output_tokens", 0) or 0

    def _finalize(self) -> None:
        if self._recorded:
            return
        self._recorded = True
        try:
            from tokenspy import pricing
            from tokenspy.tracker import CallRecord

            duration_ms = (time.perf_counter() - self._start) * 1000
            model = self._kwargs.get("model", "unknown")
            cost = pricing.calculate(model, self._input_tokens, self._output_tokens)
            fn_name = self._current_function[0] if self._current_function else "<unknown>"
            self._tracker.record(
                CallRecord(
                    function_name=fn_name,
                    call_stack=list(self._current_function),
                    model=model,
                    provider=self._provider,
                    input_tokens=self._input_tokens,
                    output_tokens=self._output_tokens,
                    cost_usd=cost,
                    duration_ms=duration_ms,
                )
            )
        except Exception:
            pass  # never crash user code

    def __enter__(self) -> _AnthropicStreamWrapper:
        if hasattr(self._stream, "__enter__"):
            self._stream.__enter__()
        return self

    def __exit__(self, *args: Any) -> Any:
        self._finalize()
        if hasattr(self._stream, "__exit__"):
            return self._stream.__exit__(*args)
        return None


def patch(tracker: Tracker, current_function: list[str]) -> bool:
    """Monkey-patch the Anthropic SDK. Returns True if successful."""
    global _original_create, _original_acreate, _patched

    try:
        from anthropic.resources.messages import Messages
    except ImportError:
        return False

    if _patched:
        return True

    _original_create = Messages.create

    def _patched_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        is_stream = kwargs.get("stream", False)
        start = time.perf_counter()
        response = _original_create(self, *args, **kwargs)

        if is_stream:
            return _AnthropicStreamWrapper(response, tracker, current_function, kwargs, start, "anthropic")

        duration_ms = (time.perf_counter() - start) * 1000
        _record(tracker, current_function, response, kwargs, duration_ms, "anthropic")
        return response

    Messages.create = _patched_create  # type: ignore[method-assign]

    # Async variant (best-effort)
    try:
        from anthropic.resources.messages import AsyncMessages

        _original_acreate = AsyncMessages.create

        async def _patched_acreate(self: Any, *args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            response = await _original_acreate(self, *args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            _record(tracker, current_function, response, kwargs, duration_ms, "anthropic")
            return response

        AsyncMessages.create = _patched_acreate  # type: ignore[method-assign]
    except Exception:
        pass

    _patched = True
    return True


def unpatch() -> None:
    global _original_create, _original_acreate, _patched

    if not _patched:
        return

    try:
        from anthropic.resources.messages import Messages

        if _original_create is not None:
            Messages.create = _original_create  # type: ignore[method-assign]

        from anthropic.resources.messages import AsyncMessages

        if _original_acreate is not None:
            AsyncMessages.create = _original_acreate  # type: ignore[method-assign]
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

        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
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
