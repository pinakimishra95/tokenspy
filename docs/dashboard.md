# Web Dashboard

tokenspy includes a local web dashboard — no cloud, no signup, runs entirely on your machine.

## Start the dashboard

```bash
pip install tokenspy[server]

tokenspy serve                          # → http://localhost:7234 (auto-opens)
tokenspy serve --port 8080              # custom port
tokenspy serve --db /path/to/custom.db  # specific database
tokenspy serve --no-open                # don't auto-open browser
```

## Overview tab

Cost/day bar chart, model breakdown donut, top functions table, live WebSocket call counter.

![tokenspy dashboard overview](assets/dashboard-overview.png)

## Traces tab

Every trace with an expandable span tree — inputs, outputs, tokens, latency, and quality scores.

![tokenspy traces view](assets/dashboard-traces.png)

## All tabs

| Tab | What you see |
|---|---|
| **Overview** | Cost/day bar chart, model donut, top functions table, live call counter |
| **Traces** | Every trace with expandable span tree — inputs, outputs, tokens, scores |
| **Evaluations** | Experiment run history, pass rates, score distributions |
| **Prompts** | Version history, production flag, content preview |
| **Settings** | DB path, OTEL endpoint status, version info |

## Real-time updates

The dashboard connects via WebSocket and updates live whenever an LLM call is recorded — useful for watching a long-running job.

## REST API

The dashboard server exposes a REST API you can query directly:

```
GET /api/summary              → overall stats
GET /api/traces               → paginated trace list
GET /api/traces/{id}          → trace + full span tree
GET /api/experiments          → experiment list
GET /api/experiments/{id}     → results table
GET /api/datasets             → dataset list
GET /api/prompts              → all prompt versions
GET /api/costs/timeseries     → cost per day
GET /api/latency/percentiles  → P50/P95/P99 per model
```

Example:

```bash
curl http://localhost:7234/api/summary
```
