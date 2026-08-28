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
            "sources": [{"label": "Letter", "author": "Buffett", "text": "quote"}],
            "follow_ups": ["next"],
        }
        with patch("rag.query_knowledge_base", return_value=result):
            response = self.client.post("/query", json={"question": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "answer")
        self.assertEqual(response.json()["sources"][0]["title"], "Letter")

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
            patch("rag.retrieve_context", return_value=("", [])),
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
            patch("rag.retrieve_context", return_value=("", [])),
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
