"""
otel.py — OpenTelemetry export for tokenspy.

Emits LLM call spans to any OTEL collector (Grafana Tempo, Jaeger,
Honeycomb, DataDog, Dynatrace, etc.) using the OpenLLMetry semantic conventions.

Usage::

    tokenspy.init(persist=True, otel_endpoint="http://localhost:4317")

    # All subsequent LLM calls are automatically exported as OTEL spans.

Install the optional dependency::

    pip install tokenspy[otel]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tokenspy.tracker import CallRecord


def configure_otel(endpoint: str, service_name: str = "tokenspy") -> None:
    """Set up OpenTelemetry export and register a hook on the global tracker.

    Args:
        endpoint: OTLP gRPC endpoint, e.g. ``"http://localhost:4317"``.
        service_name: Service name shown in the collector UI.

    Raises:
        ImportError: If ``opentelemetry-sdk`` or the OTLP exporter are not installed.
    """
    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise ImportError(
            "OpenTelemetry packages not found. Install with:\n"
            "    pip install tokenspy[otel]\n"
            "or:\n"
            "    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc"
        ) from exc

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    otel_trace.set_tracer_provider(provider)
    tracer = otel_trace.get_tracer("tokenspy", schema_url="https://opentelemetry.io/schemas/1.11.0")

    def _otel_hook(rec: CallRecord) -> None:
        # Use OpenLLMetry semantic conventions for LLM spans
        span_name = f"llm.{rec.provider}.chat"
        with tracer.start_as_current_span(span_name) as otel_span:
            # Standard LLM attributes (OpenLLMetry / GenAI semantic conventions)
            otel_span.set_attribute("llm.request.model", rec.model)
            otel_span.set_attribute("llm.provider", rec.provider)
            otel_span.set_attribute("llm.usage.prompt_tokens", rec.input_tokens)
            otel_span.set_attribute("llm.usage.completion_tokens", rec.output_tokens)
            otel_span.set_attribute("llm.usage.total_tokens", rec.total_tokens)
            otel_span.set_attribute("llm.usage.cost_usd", round(rec.cost_usd, 6))
            otel_span.set_attribute("llm.latency_ms", round(rec.duration_ms, 2))
            otel_span.set_attribute("code.function", rec.function_name)
            if rec.git_commit:
                otel_span.set_attribute("vcs.commit.id", rec.git_commit)
            if rec.session_id:
                otel_span.set_attribute("session.id", rec.session_id)

    from tokenspy.tracker import get_global_tracker
    get_global_tracker()._post_record_hooks.append(_otel_hook)
