"""
server/app.py — FastAPI application for the tokenspy dashboard.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

_static_dir = Path(__file__).parent / "static"


def create_app(db_path: str | None = None) -> Any:
    if not _FASTAPI_AVAILABLE:
        raise ImportError("pip install tokenspy[server]")

    # Determine DB path
    _db_path: Path | None = None
    if db_path:
        _db_path = Path(db_path).expanduser()
    else:
        from tokenspy.tracker import get_global_tracker
        _db_path = get_global_tracker().db_path

    app = FastAPI(title="tokenspy dashboard", docs_url=None, redoc_url=None)

    # ── WebSocket connection manager ──────────────────────────────────────────

    class ConnectionManager:
        def __init__(self) -> None:
            self.active: list[WebSocket] = []

        async def connect(self, ws: WebSocket) -> None:
            await ws.accept()
            self.active.append(ws)

        def disconnect(self, ws: WebSocket) -> None:
            self.active.remove(ws)

        async def broadcast(self, data: dict) -> None:
            for ws in list(self.active):
                try:
                    await ws.send_json(data)
                except Exception:
                    self.active.remove(ws)

    manager = ConnectionManager()

    # Register a hook to push real-time updates
    from tokenspy.tracker import get_global_tracker
    import asyncio

    def _rt_hook(rec: Any) -> None:
        import asyncio as _asyncio
        try:
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast({
                    "type": "new_call",
                    "data": {
                        "function": rec.function_name,
                        "model": rec.model,
                        "cost_usd": rec.cost_usd,
                        "tokens": rec.total_tokens,
                        "duration_ms": rec.duration_ms,
                    }
                }))
        except Exception:
            pass

    get_global_tracker()._post_record_hooks.append(_rt_hook)

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _conn() -> sqlite3.Connection | None:
        if _db_path is None or not _db_path.exists():
            return None
        return sqlite3.connect(str(_db_path))

    def _q(sql: str, params: tuple = ()) -> list:
        conn = _conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(sql, params).fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    # ── API endpoints ─────────────────────────────────────────────────────────

    @app.get("/api/summary")
    def summary() -> dict:
        from tokenspy.tracker import get_global_tracker
        return get_global_tracker().summary()

    @app.get("/api/costs/timeseries")
    def cost_timeseries(days: int = 7) -> list:
        since = time.time() - days * 86400
        rows = _q(
            "SELECT date(timestamp, 'unixepoch') as day, SUM(cost_usd), COUNT(*), SUM(input_tokens+output_tokens) "
            "FROM llm_calls WHERE timestamp >= ? GROUP BY day ORDER BY day",
            (since,),
        )
        return [{"date": r[0], "cost_usd": r[1], "calls": r[2], "tokens": r[3]} for r in rows]

    @app.get("/api/costs/by_function")
    def cost_by_function() -> list:
        rows = _q(
            "SELECT function_name, SUM(cost_usd), COUNT(*), SUM(input_tokens+output_tokens), AVG(duration_ms) "
            "FROM llm_calls GROUP BY function_name ORDER BY SUM(cost_usd) DESC LIMIT 20"
        )
        return [
            {"function": r[0], "cost_usd": r[1], "calls": r[2],
             "tokens": r[3], "avg_ms": r[4]}
            for r in rows
        ]

    @app.get("/api/costs/by_model")
    def cost_by_model() -> list:
        rows = _q(
            "SELECT model, SUM(cost_usd), COUNT(*), SUM(input_tokens+output_tokens) "
            "FROM llm_calls GROUP BY model ORDER BY SUM(cost_usd) DESC"
        )
        return [{"model": r[0], "cost_usd": r[1], "calls": r[2], "tokens": r[3]} for r in rows]

    @app.get("/api/latency/percentiles")
    def latency_percentiles() -> list:
        rows = _q("SELECT model, duration_ms FROM llm_calls ORDER BY model")
        by_model: dict[str, list[float]] = {}
        for model, ms in rows:
            by_model.setdefault(model, []).append(ms)
        result = []
        for model, vals in by_model.items():
            s = sorted(vals)
            n = len(s)
            p50 = s[int(n * 0.50)]
            p95 = s[int(n * 0.95)]
            p99 = s[int(n * 0.99)]
            result.append({"model": model, "p50": p50, "p95": p95, "p99": p99, "count": n})
        return result

    @app.get("/api/traces")
    def traces(limit: int = 50, user_id: str | None = None) -> list:
        if user_id:
            rows = _q(
                "SELECT id, name, start_time, end_time, tags, user_id, error "
                "FROM traces WHERE user_id = ? ORDER BY start_time DESC LIMIT ?",
                (user_id, limit),
            )
        else:
            rows = _q(
                "SELECT id, name, start_time, end_time, tags, user_id, error "
                "FROM traces ORDER BY start_time DESC LIMIT ?",
                (limit,),
            )
        return [
            {
                "id": r[0], "name": r[1], "start_time": r[2], "end_time": r[3],
                "duration_ms": (r[3] - r[2]) * 1000 if r[3] and r[2] else None,
                "tags": json.loads(r[4]) if r[4] else [],
                "user_id": r[5], "error": r[6],
            }
            for r in rows
        ]

    @app.get("/api/traces/{trace_id}")
    def trace_detail(trace_id: str) -> dict:
        trow = _q("SELECT * FROM traces WHERE id = ?", (trace_id,))
        if not trow:
            return {}
        t = trow[0]
        spans = _q(
            "SELECT id, parent_span_id, name, span_type, start_time, end_time, "
            "input, output, model, input_tokens, output_tokens, cost_usd, status "
            "FROM spans WHERE trace_id = ? ORDER BY start_time",
            (trace_id,),
        )
        scores = _q(
            "SELECT name, value, scorer, comment, created_at FROM scores WHERE trace_id = ?",
            (trace_id,),
        )
        return {
            "id": t[0], "name": t[1], "start_time": t[2], "end_time": t[3],
            "input": t[4], "output": t[5], "metadata": t[6],
            "tags": json.loads(t[7]) if t[7] else [],
            "spans": [
                {
                    "id": s[0], "parent_span_id": s[1], "name": s[2], "type": s[3],
                    "start_time": s[4], "end_time": s[5],
                    "duration_ms": (s[5] - s[4]) * 1000 if s[5] and s[4] else None,
                    "input": s[6], "output": s[7],
                    "model": s[8], "input_tokens": s[9], "output_tokens": s[10],
                    "cost_usd": s[11], "status": s[12],
                }
                for s in spans
            ],
            "scores": [
                {"name": s[0], "value": s[1], "scorer": s[2], "comment": s[3]} for s in scores
            ],
        }

    @app.get("/api/experiments")
    def experiments() -> list:
        rows = _q(
            "SELECT e.id, e.name, d.name as dataset, e.function_name, e.created_at, "
            "COUNT(er.id) as item_count, AVG(er.passed) as pass_rate "
            "FROM experiments e "
            "LEFT JOIN datasets d ON e.dataset_id = d.id "
            "LEFT JOIN experiment_results er ON er.experiment_id = e.id "
            "GROUP BY e.id ORDER BY e.created_at DESC"
        )
        return [
            {
                "id": r[0], "name": r[1], "dataset": r[2], "function": r[3],
                "created_at": r[4], "item_count": r[5],
                "pass_rate": round(r[6] * 100, 1) if r[6] is not None else None,
            }
            for r in rows
        ]

    @app.get("/api/datasets")
    def datasets() -> list:
        rows = _q(
            "SELECT d.id, d.name, d.description, d.created_at, COUNT(di.id) as item_count "
            "FROM datasets d LEFT JOIN dataset_items di ON di.dataset_id = d.id "
            "GROUP BY d.id ORDER BY d.created_at DESC"
        )
        return [
            {"id": r[0], "name": r[1], "description": r[2],
             "created_at": r[3], "item_count": r[4]}
            for r in rows
        ]

    @app.get("/api/prompts")
    def prompt_list() -> list:
        rows = _q(
            "SELECT name, version, prompt_type, tags, created_at, is_production, "
            "substr(content, 1, 80) as preview "
            "FROM prompts ORDER BY name, version DESC"
        )
        return [
            {
                "name": r[0], "version": r[1], "type": r[2],
                "tags": json.loads(r[3]) if r[3] else [],
                "created_at": r[4], "is_production": bool(r[5]), "preview": r[6],
            }
            for r in rows
        ]

    @app.get("/api/history")
    def history(limit: int = 50) -> list:
        rows = _q(
            "SELECT function_name, model, provider, input_tokens, output_tokens, "
            "cost_usd, duration_ms, timestamp FROM llm_calls ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [
            {
                "function": r[0], "model": r[1], "provider": r[2],
                "input_tokens": r[3], "output_tokens": r[4], "cost_usd": r[5],
                "duration_ms": r[6], "timestamp": r[7],
            }
            for r in rows
        ]

    # ── WebSocket ──────────────────────────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await manager.connect(ws)
        try:
            while True:
                await ws.receive_text()  # keep-alive
        except WebSocketDisconnect:
            manager.disconnect(ws)

    # ── Static files ───────────────────────────────────────────────────────────

    @app.get("/")
    def index() -> HTMLResponse:
        html_path = _static_dir / "index.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text())
        return HTMLResponse("<h1>tokenspy dashboard</h1><p>Static files not found.</p>")

    if _static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    return app
