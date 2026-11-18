import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fastapi import FastAPI
from fastapi.testclient import TestClient
import evidence_runtime as ledger
import english_qa as qa
from ai_gateway import ModelProfile, OpenAICompatibleAdapter


class EnglishQATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(ledger, "DB", Path(self.temp.name) / "ledger.sqlite3"),
                        patch.dict("os.environ", {"ENGLISH_PILOT_VERIFY": "false"})]
        for p in self.patches:
            p.start()
        app = FastAPI()
        app.include_router(qa.router)
        self.client = TestClient(app)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def test_reserved_failures_count_against_limit(self):
        with patch.dict("os.environ", {"ENGLISH_PILOT_CALL_LIMIT": "2"}):
            a = ledger.reserve("answer", "test")
            ledger.settle(a, "failed")
            ledger.reserve("answer", "test")
            with self.assertRaises(RuntimeError):
                ledger.reserve("answer", "test")
            with ledger.connection() as c:
                self.assertIsNone(c.execute("SELECT usage FROM calls WHERE id=?", (a,)).fetchone()[0])

    def test_original_route_preserves_unknown_speakers(self):
        cid = "cnbc-meeting-1998-afternoon-ch08"
        result = self.client.get("/api/english/sources/" + cid)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(any(p["speaker"] is None for p in result.json()["paragraphs"]))
        self.assertEqual(self.client.get("/api/english/sources/missing").status_code, 404)

    def test_unknown_citation_and_quote_do_not_claim_validation(self):
        sources = [{"full_context": "The exact original sentence is preserved here."}]
        self.assertEqual(qa.reference_checks("Supported point. [1]", sources)["status"], "references_checked")
        self.assertEqual(qa.reference_checks("Unsupported reference. [9]", sources)["status"], "needs_review")
        self.assertEqual(qa.reference_checks('“This quotation was invented completely.” [1]', sources)["status"], "needs_review")

    def test_short_quotes_do_not_capture_prose_between_them(self):
        answer = 'The phrase "Judgment Day" is short; the following long explanation is not quoted, and neither is "cash flow". [1]'
        self.assertEqual(qa.reference_checks(answer, [{"full_context": "Judgment Day and cash flow."}])["status"], "references_checked")

    def test_quote_typography_does_not_change_words(self):
        source = [{"full_context": "We don’t know what the future will bring."}]
        self.assertEqual(qa.reference_checks('"We don\'t know what the future will bring," [1]', source)["status"], "references_checked")
        self.assertEqual(qa.reference_checks('"We know what the future will bring," [1]', source)["status"], "needs_review")

    def test_stream_replay_never_generates_again(self):
        calls = []
        class Gateway:
            routes = {"knowledge_answer": SimpleNamespace(primary="default", fallbacks=())}
            profiles = {"default": SimpleNamespace(provider="openai_compatible", model="test", max_retries=0)}
            def stream(self, *args, **kwargs):
                calls.append(1)
                yield "An explanation. "
                yield "[1]"
                kwargs["observer"]({"type": "finish", "reason": "stop"})
                kwargs["observer"]({"type": "usage", "input_tokens": 8, "output_tokens": 4})
        selected = [{"context_id": "letter-1994-0013-0026", "matched_paragraph_ids": []}]
        payload = {"question": "What is intrinsic value?", "request_id": str(uuid4())}
        with patch.object(qa, "retrieve", return_value=(selected, {})), patch.object(qa, "get_generation_gateway", return_value=Gateway()):
            first = self.client.post("/api/english/ask", json=payload)
            events = [json.loads(line[6:]) for line in first.text.splitlines() if line.startswith("data: ")]
            self.assertEqual([x["type"] for x in events], ["status", "sources", "status", "token", "token", "done"])
            second = self.client.post("/api/english/ask", json=payload)
            self.assertIn('"replay": true', second.text)
            self.assertEqual(calls, [1])
            payload["question"] = "A different question"
            self.assertEqual(self.client.post("/api/english/ask", json=payload).status_code, 409)

    def test_incomplete_stream_is_not_a_finished_answer(self):
        class Gateway:
            routes = {"knowledge_answer": SimpleNamespace(primary="default", fallbacks=())}
            profiles = {"default": SimpleNamespace(provider="openai_compatible", model="test", max_retries=0)}
            def stream(self, *args, **kwargs):
                yield "Partial [1]"
                kwargs["observer"]({"type": "finish", "reason": "length"})
        payload = {"question": "What is intrinsic value?", "request_id": str(uuid4())}
        selected = [{"context_id": "letter-1994-0013-0026", "matched_paragraph_ids": []}]
        with patch.object(qa, "retrieve", return_value=(selected, {})), patch.object(qa, "get_generation_gateway", return_value=Gateway()):
            result = self.client.post("/api/english/ask", json=payload)
            self.assertIn('"type": "error"', result.text)
            self.assertNotIn('"type": "done"', result.text)
            self.assertEqual(self.client.post("/api/english/ask", json=payload).status_code, 409)
        self.assertTrue(qa.BUSY.acquire(blocking=False))
        qa.BUSY.release()

    def test_cross_origin_cannot_spend(self):
        payload = {"question": "What is value?", "request_id": str(uuid4())}
        response = self.client.post("/api/english/ask", json=payload, headers={"Origin": "https://unrelated.example"})
        self.assertEqual(response.status_code, 403)

    def test_empty_provider_chunks_still_obey_total_timeout(self):
        client = MagicMock()
        client.__enter__.return_value = client
        stream_context = client.chat.completions.create.return_value
        stream_context.__enter__.return_value = iter([SimpleNamespace(choices=[], usage=None)])
        profile = ModelProfile("test", "openai_compatible", "test", timeout=1, max_retries=0)
        adapter = OpenAICompatibleAdapter()
        with patch.object(adapter, "_client", return_value=client), patch("ai_gateway.time.monotonic", side_effect=[0, 2]):
            with self.assertRaises(TimeoutError):
                list(adapter.stream(profile, system="", messages=[], max_tokens=10, temperature=None, observer=lambda _: None))
        stream_context.__exit__.assert_called_once()
        client.__exit__.assert_called_once()

    def test_cleanup_failure_still_releases_concurrency_slot(self):
        payload = qa.Ask(question="What is value?", request_id=uuid4())
        qa.BUSY.acquire()
        with patch.object(qa, "retrieve", side_effect=RuntimeError("failure")), patch.object(qa, "finish", side_effect=OSError("ledger unavailable")):
            with self.assertRaises(OSError):
                list(qa.stream_answer(payload))
        self.assertTrue(qa.BUSY.acquire(blocking=False))
        qa.BUSY.release()


if __name__ == "__main__":
    unittest.main()
