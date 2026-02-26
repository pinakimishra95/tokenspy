"""Tests for streaming response support (stream=True)."""

from __future__ import annotations

import types

from tokenspy.tracker import Tracker

# ── OpenAI streaming ──────────────────────────────────────────────────────────

def _make_usage(prompt_tokens: int, completion_tokens: int) -> object:
    u = types.SimpleNamespace()
    u.prompt_tokens = prompt_tokens
    u.completion_tokens = completion_tokens
    return u


def _make_openai_chunks(prompt_tokens: int, completion_tokens: int):
    """Yield fake OpenAI streaming chunks; last chunk carries usage."""
    for i in range(3):
        chunk = types.SimpleNamespace()
        chunk.usage = None  # intermediate chunks have no usage
        chunk.choices = [types.SimpleNamespace(delta=types.SimpleNamespace(content=f"word{i}"))]
        yield chunk
    # Final chunk with usage (from include_usage=True)
    final = types.SimpleNamespace()
    final.usage = _make_usage(prompt_tokens, completion_tokens)
    final.choices = []
    yield final


class TestOpenAIStreamWrapper:
    def test_wrapper_records_after_iteration(self):
        from tokenspy.providers.openai import _OpenAIStreamWrapper

        tracker = Tracker()
        fn = ["my_func"]
        chunks = list(_make_openai_chunks(100, 50))
        wrapper = _OpenAIStreamWrapper(iter(chunks), tracker, fn,
                                       {"model": "gpt-4o"}, 0.0, "openai")

        collected = list(wrapper)
        assert len(collected) == 4  # 3 + 1 final
        recs = tracker.records()
        assert len(recs) == 1
        assert recs[0].input_tokens == 100
        assert recs[0].output_tokens == 50
        assert recs[0].model == "gpt-4o"
        assert recs[0].provider == "openai"
        assert recs[0].function_name == "my_func"

    def test_wrapper_no_usage_does_not_record(self):
        from tokenspy.providers.openai import _OpenAIStreamWrapper

        tracker = Tracker()
        fn = ["my_func"]
        # All chunks have no usage
        chunks = [types.SimpleNamespace(usage=None, choices=[]) for _ in range(3)]
        wrapper = _OpenAIStreamWrapper(iter(chunks), tracker, fn,
                                       {"model": "gpt-4o"}, 0.0, "openai")
        list(wrapper)
        assert tracker.total_calls() == 0

    def test_patched_create_injects_stream_options(self):
        """Patched create injects include_usage when stream=True."""
        from openai.resources.chat.completions import Completions

        from tokenspy.providers import openai as _op

        tracker = Tracker()
        captured_kwargs: list[dict] = []

        def fake_original(self, *args, **kwargs):
            captured_kwargs.append(dict(kwargs))
            return iter(_make_openai_chunks(10, 5))

        # Set fake directly on the class so patch() saves it as _original_create
        Completions.create = fake_original
        _op._patched = False
        _op._original_create = None
        _op.patch(tracker, ["test_fn"])

        c = Completions()
        result = c.create(model="gpt-4o", messages=[], stream=True)
        list(result)

        assert captured_kwargs[0].get("stream_options", {}).get("include_usage") is True

    def test_patched_create_non_stream_unaffected(self):
        """Non-streaming calls still work as before."""
        from openai.resources.chat.completions import Completions

        from tokenspy.providers import openai as _op

        tracker = Tracker()

        def fake_original(self, *args, **kwargs):
            resp = types.SimpleNamespace()
            resp.usage = _make_usage(20, 10)
            return resp

        Completions.create = fake_original
        _op._patched = False
        _op._original_create = None
        _op.patch(tracker, ["test_fn"])

        c = Completions()
        result = c.create(model="gpt-4o-mini", messages=[])
        # Should NOT be a wrapper — just the response
        assert not hasattr(result, "_stream")
        assert tracker.total_calls() == 1
        assert tracker.records()[0].input_tokens == 20


# ── Anthropic streaming ───────────────────────────────────────────────────────

def _make_anthropic_events(input_tokens: int, output_tokens: int):
    """Yield fake Anthropic streaming events."""
    # message_start
    start_usage = types.SimpleNamespace(input_tokens=input_tokens)
    start_msg = types.SimpleNamespace(usage=start_usage)
    yield types.SimpleNamespace(type="message_start", message=start_msg)
    # content delta
    yield types.SimpleNamespace(type="content_block_delta",
                                 delta=types.SimpleNamespace(text="hello "))
    yield types.SimpleNamespace(type="content_block_delta",
                                 delta=types.SimpleNamespace(text="world"))
    # message_delta with output tokens
    delta_usage = types.SimpleNamespace(output_tokens=output_tokens)
    yield types.SimpleNamespace(type="message_delta", usage=delta_usage)
    # message_stop
    yield types.SimpleNamespace(type="message_stop")


class TestAnthropicStreamWrapper:
    def test_wrapper_records_after_iteration(self):
        from tokenspy.providers.anthropic import _AnthropicStreamWrapper

        tracker = Tracker()
        fn = ["my_agent"]
        events = list(_make_anthropic_events(200, 75))
        wrapper = _AnthropicStreamWrapper(iter(events), tracker, fn,
                                          {"model": "claude-haiku-4-5"}, 0.0, "anthropic")
        collected = list(wrapper)
        assert len(collected) == 5
        recs = tracker.records()
        assert len(recs) == 1
        assert recs[0].input_tokens == 200
        assert recs[0].output_tokens == 75
        assert recs[0].model == "claude-haiku-4-5"
        assert recs[0].provider == "anthropic"

    def test_wrapper_records_only_once(self):
        """Calling finalize multiple times should not double-record."""
        from tokenspy.providers.anthropic import _AnthropicStreamWrapper

        tracker = Tracker()
        fn = ["my_agent"]
        events = list(_make_anthropic_events(50, 30))
        wrapper = _AnthropicStreamWrapper(iter(events), tracker, fn,
                                          {"model": "claude-haiku-4-5"}, 0.0, "anthropic")
        list(wrapper)
        wrapper._finalize()  # call again — should be no-op
        assert tracker.total_calls() == 1

    def test_patched_create_stream_returns_wrapper(self):
        from anthropic.resources.messages import Messages

        from tokenspy.providers import anthropic as _ap

        tracker = Tracker()

        def fake_original(self, *args, **kwargs):
            return iter(_make_anthropic_events(100, 40))

        Messages.create = fake_original
        _ap._patched = False
        _ap._original_create = None
        _ap.patch(tracker, ["test_fn"])

        m = Messages()
        result = m.create(model="claude-haiku-4-5", messages=[], stream=True)
        from tokenspy.providers.anthropic import _AnthropicStreamWrapper
        assert isinstance(result, _AnthropicStreamWrapper)
        list(result)
        assert tracker.total_calls() == 1
        assert tracker.records()[0].input_tokens == 100
