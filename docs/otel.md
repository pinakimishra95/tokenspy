# OpenTelemetry Export

Send tokenspy data to **Grafana, Jaeger, Datadog, Honeycomb** — any OTEL-compatible backend.

## Setup

```bash
pip install tokenspy[otel]
```

```python
tokenspy.init(
    persist=True,
    otel_endpoint="http://localhost:4317",   # your OTLP gRPC endpoint
    otel_service_name="my-llm-app",
)
```

Every LLM call is exported as an OpenTelemetry span with standard attributes:

```
llm.openai.chat
  llm.request.model:           "gpt-4o"
  llm.usage.prompt_tokens:     4200
  llm.usage.completion_tokens: 380
  llm.usage.cost_usd:          0.0144
  code.function:               "summarize"
```

## What this unlocks

- **Grafana** — cost per minute, P95 latency, error rate dashboards
- **Jaeger** — distributed trace view across microservices
- **Datadog** — alert when cost per request exceeds threshold
- **Honeycomb** — slice and dice by model, function, user

## Running a local OTEL collector

Quick test with Docker:

```bash
docker run -p 4317:4317 otel/opentelemetry-collector-contrib
```

## Collector config example (Grafana)

```yaml
exporters:
  prometheusremotewrite:
    endpoint: "http://your-grafana/api/prom/push"

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [prometheusremotewrite]
```
