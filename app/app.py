#!/usr/bin/env python3
"""Small dependency-free HTTP service for SRE and monitoring demos."""

from __future__ import annotations

import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar


class Metrics:
    """Thread-safe in-memory metrics used by the demo service."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.requests_total = 0
        self.failures_total = 0

    def record(self, *, failed: bool = False) -> None:
        with self._lock:
            self.requests_total += 1
            if failed:
                self.failures_total += 1

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            return {
                "requests_total": self.requests_total,
                "failures_total": self.failures_total,
                "uptime_seconds": max(0.0, time.time() - self.started_at),
            }


METRICS = Metrics()
STATIC_DIR = Path(__file__).with_name("static")


class Handler(BaseHTTPRequestHandler):
    """HTTP routes for health checks, metrics and failure simulation."""

    server_version: ClassVar[str] = "SelfHealingDemo/1.0"

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: HTTPStatus, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_file(self, filename: str, content_type: str) -> None:
        """Serve a trusted file from the bundled static directory."""
        try:
            body = (STATIC_DIR / filename).read_bytes()
        except FileNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        static_files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        if path in static_files:
            METRICS.record()
            self._send_file(*static_files[path])
            return

        if path == "/health":
            unhealthy = os.getenv("FORCE_UNHEALTHY", "false").lower() == "true"
            METRICS.record(failed=unhealthy)
            if unhealthy:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unhealthy"})
            else:
                self._send_json(HTTPStatus.OK, {"status": "healthy"})
            return

        if path == "/ready":
            METRICS.record()
            self._send_json(HTTPStatus.OK, {"status": "ready"})
            return

        if path == "/fail":
            METRICS.record(failed=True)
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"status": "failed", "message": "Synthetic failure for alert testing"},
            )
            return

        if path == "/metrics":
            METRICS.record()
            snapshot = METRICS.snapshot()
            body = "\n".join(
                [
                    "# HELP demo_http_requests_total Total HTTP requests handled.",
                    "# TYPE demo_http_requests_total counter",
                    f"demo_http_requests_total {snapshot['requests_total']}",
                    "# HELP demo_http_failures_total Total synthetic or health failures.",
                    "# TYPE demo_http_failures_total counter",
                    f"demo_http_failures_total {snapshot['failures_total']}",
                    "# HELP demo_process_uptime_seconds Process uptime in seconds.",
                    "# TYPE demo_process_uptime_seconds gauge",
                    f"demo_process_uptime_seconds {snapshot['uptime_seconds']:.3f}",
                    "",
                ]
            )
            self._send_text(HTTPStatus.OK, body, "text/plain; version=0.0.4")
            return

        METRICS.record(failed=True)
        self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})

    def log_message(self, format: str, *args: object) -> None:
        print(json.dumps({"client": self.client_address[0], "message": format % args}))


def create_server(host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    server = create_server(port=port)
    print(f"Listening on 0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
