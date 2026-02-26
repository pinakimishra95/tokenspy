"""Tests for LangChain callback handler integration."""

from __future__ import annotations

import sys
import types

from tokenspy.tracker import Tracker


def _make_langchain_stub() -> None:
    """Stub langchain_core in sys.modules so the integration can be imported."""
    if "langchain_core" in sys.modules:
        return

    langchain_core = types.ModuleType("langchain_core")
    callbacks_mod = types.ModuleType("langchain_core.callbacks")
    base_mod = types.ModuleType("langchain_core.callbacks.base")
    outputs_mod = types.ModuleType("langchain_core.outputs")

    class BaseCallbackHandler:
        def on_llm_start(self, *args, **kwargs): pass
        def on_llm_end(self, *args, **kwargs): pass
        def on_llm_error(self, *args, **kwargs): pass

    class LLMResult:
        def __init__(self, llm_output=None, generations=None):
            self.llm_output = llm_output
            self.generations = generations or []

    base_mod.BaseCallbackHandler = BaseCallbackHandler
    outputs_mod.LLMResult = LLMResult
    callbacks_mod.base = base_mod
    langchain_core.callbacks = callbacks_mod
    langchain_core.outputs = outputs_mod

    sys.modules["langchain_core"] = langchain_core
    sys.modules["langchain_core.callbacks"] = callbacks_mod
    sys.modules["langchain_core.callbacks.base"] = base_mod
    sys.modules["langchain_core.outputs"] = outputs_mod


_make_langchain_stub()


class TestTokenspyCallbackHandler:
    def test_on_llm_end_records_openai_call(self):
        from langchain_core.outputs import LLMResult

        from tokenspy.integrations.langchain import TokenspyCallbackHandler

        tracker = Tracker()
        handler = TokenspyCallbackHandler(tracker=tracker)

        # Simulate on_llm_start
        handler.on_llm_start({}, ["Hello, world!"])

        # Simulate on_llm_end with OpenAI-style token_usage
        result = LLMResult(
            llm_output={
                "model_name": "gpt-4o-mini",
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                },
            }
        )
        handler.on_llm_end(result)

        recs = tracker.records()
        assert len(recs) == 1
        assert recs[0].input_tokens == 100
        assert recs[0].output_tokens == 50
        assert recs[0].model == "gpt-4o-mini"
        assert recs[0].provider == "langchain"
        assert recs[0].cost_usd > 0

    def test_on_llm_end_records_anthropic_call(self):
        from langchain_core.outputs import LLMResult

        from tokenspy.integrations.langchain import TokenspyCallbackHandler

        tracker = Tracker()
        handler = TokenspyCallbackHandler(tracker=tracker)
        handler.on_llm_start({}, ["test"])

        result = LLMResult(
            llm_output={
                "model_name": "claude-haiku-4-5",
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 80,
                },
            }
        )
        handler.on_llm_end(result)

        recs = tracker.records()
        assert len(recs) == 1
        assert recs[0].input_tokens == 200
        assert recs[0].output_tokens == 80
        assert recs[0].model == "claude-haiku-4-5"

    def test_on_llm_end_without_start_does_not_record(self):
        from langchain_core.outputs import LLMResult

        from tokenspy.integrations.langchain import TokenspyCallbackHandler

        tracker = Tracker()
        handler = TokenspyCallbackHandler(tracker=tracker)
        # No on_llm_start — on_llm_end should be a no-op
        result = LLMResult(llm_output={"model_name": "gpt-4o", "token_usage": {}})
        handler.on_llm_end(result)
        assert tracker.total_calls() == 0

    def test_on_llm_error_resets_start(self):
        from langchain_core.outputs import LLMResult

        from tokenspy.integrations.langchain import TokenspyCallbackHandler

        tracker = Tracker()
        handler = TokenspyCallbackHandler(tracker=tracker)
        handler.on_llm_start({}, ["test"])
        handler.on_llm_error(RuntimeError("API error"))
        # After error, on_llm_end should not record
        result = LLMResult(llm_output={"model_name": "gpt-4o"})
        handler.on_llm_end(result)
        assert tracker.total_calls() == 0

    def test_handler_uses_global_tracker_by_default(self):

        from tokenspy.integrations.langchain import TokenspyCallbackHandler
        from tokenspy.tracker import get_global_tracker

        handler = TokenspyCallbackHandler()
        assert handler._tracker is get_global_tracker()

    def test_duration_is_positive(self):
        import time

        from langchain_core.outputs import LLMResult

        from tokenspy.integrations.langchain import TokenspyCallbackHandler

        tracker = Tracker()
        handler = TokenspyCallbackHandler(tracker=tracker)
        handler.on_llm_start({}, ["test"])
        time.sleep(0.01)
        result = LLMResult(
            llm_output={"model_name": "gpt-4o", "token_usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        )
        handler.on_llm_end(result)
        assert tracker.records()[0].duration_ms >= 10
