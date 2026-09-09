import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

import server


class _FakeGenerationGateway:
    def complete(self, task, **kwargs):
        if task == "structured_feedback":
            return SimpleNamespace(text='{"feedback":"ok","key_concepts":["moat"]}')
        return SimpleNamespace(text="generated")


class _InvalidStructuredGateway:
    def complete(self, task, **kwargs):
        return SimpleNamespace(text="not-json")


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app)

    def test_query_contract_is_preserved(self):
        result = {
            "answer": "answer",
            "sources": [{"label": "Letter", "author": "Buffett", "text": "quote", "year": 1988, "url": "https://example.org/letter"}],
            "follow_ups": ["next"],
        }
        with patch("rag.query_knowledge_base", return_value=result):
            response = self.client.post("/query", json={"question": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "answer")
        self.assertEqual(response.json()["sources"][0]["title"], "Letter")
        self.assertEqual(response.json()["sources"][0]["year"], 1988)
        self.assertEqual(response.json()["sources"][0]["url"], "https://example.org/letter")

    def test_query_failure_has_service_status_without_internal_details(self):
        with patch("rag.query_knowledge_base", return_value={"answer": "", "error": "secret-internal-error", "error_code": "KNOWLEDGE_NOT_READY"}):
            response = self.client.post("/query", json={"question": "test"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret-internal-error", response.text)
        self.assertEqual(response.json()["sources"], [])

    def test_gym_without_sources_does_not_generate_feedback_or_synthesis(self):
        for endpoint, payload in [
            ("/gym/feedback", {"case_id": "cocacola", "round": 0, "question": "q", "answer": "a"}),
            ("/gym/synthesis", {"case_id": "cocacola", "answers": ["a"], "feedbacks": []}),
        ]:
            with patch("rag.retrieve_context", return_value=("", [])), patch.object(server, "get_generation_gateway") as gateway:
                response = self.client.post(endpoint, json=payload)
            self.assertEqual(response.status_code, 503)
            gateway.assert_not_called()

    def test_health_distinguishes_liveness_from_knowledge_readiness(self):
        gateway = SimpleNamespace(status=lambda: {})
        for index, configured, expected in [
            ({"count": None, "status": "unavailable"}, True, "index_unavailable"),
            ({"count": 0, "status": "empty"}, True, "index_empty"),
            ({"count": 5, "status": "populated"}, False, "embedding_not_configured"),
        ]:
            with patch.object(server, "index_status", return_value=index), \
                 patch.object(server, "get_embedding_gateway", return_value=SimpleNamespace(status=lambda: {"configured": configured})), \
                 patch.object(server, "get_generation_gateway", return_value=gateway), \
                 patch.object(server, "get_reranker_gateway", return_value=gateway):
                response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")
            self.assertEqual(response.json()["knowledge_status"], expected)

    def test_digest_uses_generation_gateway(self):
        with patch.object(server, "get_generation_gateway", return_value=_FakeGenerationGateway()):
            response = self.client.post("/api/digest", json={"prompt": "p", "system": "s"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"content": "generated"})

    def test_structured_feedback_contract_is_preserved(self):
        payload = {
            "case_id": "cocacola",
            "round": 0,
            "question": "q",
            "answer": "a",
            "language": "cn",
        }
        with (
            patch.object(server, "get_generation_gateway", return_value=_FakeGenerationGateway()),
            patch("rag.retrieve_context", return_value=("[来源1] reference", [{"label": "Letter"}])),
        ):
            response = self.client.post("/gym/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["feedback"], "ok")
        self.assertEqual(response.json()["key_concepts"], ["moat"])

    def test_invalid_structured_feedback_is_rejected(self):
        payload = {
            "case_id": "cocacola",
            "round": 0,
            "question": "q",
            "answer": "a",
            "language": "cn",
        }
        with (
            patch.object(server, "get_generation_gateway", return_value=_InvalidStructuredGateway()),
            patch("rag.retrieve_context", return_value=("[来源1] reference", [{"label": "Letter"}])),
        ):
            response = self.client.post("/gym/feedback", json=payload)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "MODEL_OUTPUT_INVALID")

    def test_streaming_chat_keeps_sse_media_type(self):
        events = iter([
            'data: {"type":"token","text":"a"}\n\n',
            'data: {"type":"done","final_answer":"a"}\n\n',
        ])
        with patch("rag.stream_query_knowledge_base", return_value=events):
            response = self.client.post("/api/chat/stream", json={"query": "q", "history": []})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertIn('"type":"done"', response.text)


if __name__ == "__main__":
    unittest.main()
