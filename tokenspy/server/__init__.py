"""
tokenspy.server — Local web dashboard.

Start with::

    tokenspy serve          # default: http://localhost:7234
    tokenspy serve --port 8080

Or from Python::

    from tokenspy.server import serve
    serve(port=7234)

Requires: pip install tokenspy[server]
"""

from __future__ import annotations

import webbrowser
from pathlib import Path


def serve(
    port: int = 7234,
    db_path: str | None = None,
    open_browser: bool = True,
    host: str = "127.0.0.1",
) -> None:
    """Start the tokenspy dashboard server.

    Args:
        port: Port to listen on (default: 7234).
        db_path: Path to SQLite database. Defaults to global tracker's db_path.
        open_browser: If True, opens the dashboard in the default browser.
        host: Host to bind to (default: 127.0.0.1).
    """
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "Dashboard requires FastAPI and uvicorn. Install with:\n"
            "    pip install tokenspy[server]\n"
            "or:\n"
            "    pip install fastapi uvicorn"
        ) from exc

    from tokenspy.server.app import create_app

    app = create_app(db_path=db_path)
    url = f"http://{host}:{port}"
    print(f"[tokenspy] Dashboard running at {url}")
    print("[tokenspy] Press Ctrl+C to stop.\n")

    if open_browser:
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")
