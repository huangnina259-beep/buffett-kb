import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fastapi import FastAPI
from fastapi.testclient import TestClient
import evidence_runtime as ledger
import english_qa as qa


class TwoPassGateway:
    routes = {"knowledge_answer": SimpleNamespace(primary="default", fallbacks=())}
    profiles = {"default": SimpleNamespace(provider="openai_compatible", model="test", max_retries=0)}

    def __init__(self, review_finish="stop", interrupt_review=False):
        self.calls = []
        self.review_finish = review_finish
        self.interrupt_review = interrupt_review

    def stream(self, task, **kwargs):
        self.calls.append((task, kwargs))
        if len(self.calls) == 1:
            yield "Draft assertion with an invalid reference. [99]"
            kwargs["observer"]({"type": "usage", "input_tokens": 8, "output_tokens": 4})
            kwargs["observer"]({"type": "finish", "reason": "stop"})
        else:
            if self.interrupt_review:
                raise GeneratorExit()
            yield "Corrected explanation "
            yield "from the originals. [1]"
            kwargs["observer"]({"type": "usage", "input_tokens": 12, "output_tokens": 6})
            kwargs["observer"]({"type": "finish", "reason": self.review_finish})


class EnglishVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.gateway = TwoPassGateway()
        selected = [{"context_id": "letter-1994-0013-0026", "matched_paragraph_ids": []}]
        self.patches = [
            patch.object(ledger, "DB", Path(self.temp.name) / "ledger.sqlite3"),
            patch.dict("os.environ", {"ENGLISH_PILOT_VERIFY": "true", "ENGLISH_PILOT_CALL_LIMIT": "8"}),
            patch.object(qa, "retrieve", return_value=(selected, {})),
            patch.object(qa, "get_generation_gateway", return_value=self.gateway),
        ]
        for item in self.patches:
            item.start()
        app = FastAPI()
        app.include_router(qa.router)
        self.client = TestClient(app)
        self.payload = {"question": "What is intrinsic value?", "request_id": str(uuid4())}

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    @staticmethod
    def events(response):
        return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]

    def rows(self):
        with ledger.connection() as conn:
            return [dict(row) for row in conn.execute("SELECT stage,status,usage FROM calls ORDER BY id")]

    def assert_slot_free(self):
        self.assertTrue(qa.BUSY.acquire(blocking=False))
        qa.BUSY.release()

    def test_corrected_final_answer_two_reservations_and_free_replay(self):
        events = self.events(self.client.post("/api/english/ask", json=self.payload))
        tokens = [item["text"] for item in events if item["type"] == "token"]
        self.assertEqual(tokens, ["Draft assertion with an invalid reference. [99]"])
        self.assertTrue(any(item.get("message") == "Checking the answer against the original passages…" for item in events))
        final = events[-1]
        self.assertEqual(final["type"], "done")
        self.assertEqual(final["answer"], "Corrected explanation from the originals. [1]")
        self.assertEqual(final["validation"]["status"], "references_checked")
        self.assertEqual(final["usage"]["input_tokens"], 20)
        self.assertEqual(final["usage"]["output_tokens"], 10)
        self.assertEqual(final["usage_by_stage"]["grounding_review"]["input_tokens"], 12)
        self.assertTrue(final["prompt_version"].endswith("-verification-1"))
        self.assertGreaterEqual(final["timings"]["reviewer_start_ms"], final["timings"]["retrieval_ms"])
        self.assertGreaterEqual(final["timings"]["reviewer_ms"], 0)
        self.assertEqual([(row["stage"], row["status"]) for row in self.rows()], [("answer", "completed"), ("grounding_review", "completed")])
        self.assertEqual(len(self.gateway.calls), 2)
        self.assertEqual(self.gateway.calls[0][1]["system"], self.gateway.calls[1][1]["system"])
        self.assertEqual(self.gateway.calls[1][1]["max_tokens"], 12000)
        self.assertIn("Draft assertion with an invalid reference", self.gateway.calls[1][1]["messages"][-1]["content"])
        replay = self.events(self.client.post("/api/english/ask", json=self.payload))
        self.assertTrue(replay[-1]["replay"])
        self.assertEqual(replay[-1]["answer"], final["answer"])
        self.assertEqual(len(self.gateway.calls), 2)
        self.assertEqual(len(self.rows()), 2)
        self.assert_slot_free()

    def test_review_truncation_leaves_draft_unvalidated_and_settles_both_calls(self):
        self.gateway.review_finish = "length"
        events = self.events(self.client.post("/api/english/ask", json=self.payload))
        self.assertEqual(events[-1]["type"], "error")
        self.assertNotIn("done", [item["type"] for item in events])
        self.assertEqual([item["text"] for item in events if item["type"] == "token"], ["Draft assertion with an invalid reference. [99]"])
        self.assertEqual([(row["stage"], row["status"]) for row in self.rows()], [("answer", "completed"), ("grounding_review", "failed_or_interrupted")])
        self.assertEqual(json.loads(self.rows()[1]["usage"])["output_tokens"], 6)
        self.assertEqual(self.client.post("/api/english/ask", json=self.payload).status_code, 409)
        self.assertEqual(len(self.gateway.calls), 2)
        self.assert_slot_free()

    def test_review_interruption_preserves_writer_charge_and_releases_slot(self):
        self.gateway.interrupt_review = True
        payload = qa.Ask(**self.payload)
        ledger.claim(self.payload["request_id"], "test-fingerprint")
        self.assertTrue(qa.BUSY.acquire(blocking=False))
        with self.assertRaises(GeneratorExit):
            list(qa.stream_answer(payload))
        rows = self.rows()
        self.assertEqual([(row["stage"], row["status"]) for row in rows], [("answer", "completed"), ("grounding_review", "failed_or_interrupted")])
        self.assertIsNone(rows[1]["usage"])
        with ledger.connection() as conn:
            self.assertEqual(conn.execute("SELECT status FROM requests WHERE id=?", (self.payload["request_id"],)).fetchone()[0], "failed_or_interrupted")
        self.assert_slot_free()

    def test_partial_usage_is_not_counted_as_zero(self):
        self.assertEqual(qa.combined_usage([{"input_tokens": 4, "output_tokens": 2}, None]), {"type": "usage", "input_tokens": None, "output_tokens": None})


if __name__ == "__main__":
    unittest.main()
