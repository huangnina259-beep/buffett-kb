import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fastapi.testclient import TestClient
import english_app
import english_qa


class EnglishAppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(english_app.app)

    def test_legacy_ai_and_write_routes_are_not_mounted(self):
        cases = [
            ("GET", "/api/ai/settings"),
            ("PUT", "/api/ai/settings"),
            ("POST", "/api/ai/test"),
            ("GET", "/api/coach/state"),
            ("POST", "/api/coach/state"),
            ("POST", "/api/coach/stream"),
            ("POST", "/query"),
            ("POST", "/api/tutor/stream"),
            ("GET", "/openapi.json"),
        ]
        for method, path in cases:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.client.request(method, path).status_code, 404)

    def test_homepage_and_existing_english_router_are_available(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/english").status_code, 200)
        with patch.object(english_qa, "ready_index", return_value=(None, {"contexts": 14})):
            response = self.client.get("/api/english/status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ready"])
        source = self.client.get("/api/english/sources/cnbc-meeting-1998-afternoon-ch08")
        self.assertEqual(source.status_code, 200)
        self.assertEqual(source.json()["context_id"], "cnbc-meeting-1998-afternoon-ch08")
        # Validate routing without spending a call or creating a ledger request.
        self.assertEqual(self.client.post("/api/english/ask", json={}).status_code, 422)

    def test_health_reports_valid_index_only(self):
        with patch.object(english_app, "ready_index", return_value=(None, {"contexts": 14})):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source_contexts"], 14)
        self.assertTrue(response.json()["index_ready"])
        self.assertIn("provider access and answer quality are not tested", response.json()["scope"])

    def test_health_fails_closed_without_exposing_exception(self):
        with patch.object(english_app, "ready_index", side_effect=RuntimeError("private diagnostic")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["index_ready"])
        self.assertNotIn("private diagnostic", response.text)


if __name__ == "__main__":
    unittest.main()
