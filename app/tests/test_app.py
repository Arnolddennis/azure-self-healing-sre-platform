from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from app import create_server


class DemoServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server(host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get_json(self, path: str) -> tuple[int, dict[str, object]]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_endpoint(self) -> None:
        status, body = self.get_json("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "healthy")

    def test_ready_endpoint(self) -> None:
        status, body = self.get_json("/ready")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ready")

    def test_failure_endpoint_returns_500(self) -> None:
        with self.assertRaises(HTTPError) as context:
            urlopen(f"http://127.0.0.1:{self.port}/fail", timeout=2)
        self.assertEqual(context.exception.code, 500)

    def test_metrics_endpoint(self) -> None:
        with urlopen(f"http://127.0.0.1:{self.port}/metrics", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("demo_http_requests_total", body)
        self.assertIn("demo_http_failures_total", body)


if __name__ == "__main__":
    unittest.main()
