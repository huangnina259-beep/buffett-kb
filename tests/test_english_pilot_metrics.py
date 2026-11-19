import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from fastapi.testclient import TestClient
import english_app
import english_qa as qa
import evidence_runtime as ledger
from review_english_pilot import read_report


class MetricsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "ledger.sqlite3"
        self.addCleanup(patch.stopall)
        patch.object(ledger, "DB", self.db).start()
        self.client = TestClient(english_app.app)
        self.request = str(uuid4())

    def test_exit_during_request_is_idempotent_and_does_not_change_server_outcome(self):
        payload = {"request_id": self.request, "event": "pagehide", "elapsed_ms": 1200}
        url = "/api/english/left"
        self.assertEqual(self.client.post(url, json=payload).status_code, 404)
        ledger.claim(self.request, "fingerprint", "Why would inventory rise?", "english_form")
        ledger.record_first_token(self.request, 900)
        self.assertEqual(self.client.post(url, json=payload, headers={"origin": "https://other.example"}).status_code, 403)
        self.assertEqual(self.client.post(url, json={**payload, "event": "arbitrary"}).status_code, 422)
        self.assertEqual(self.client.post(url, json=payload, headers={"origin": "http://testserver"}).status_code, 200)
        self.assertEqual(self.client.post(url, json={**payload, "elapsed_ms": 1800}).status_code, 200)
        report = read_report(self.db)
        row = report["requests"][0]
        self.assertEqual(row["server_status"], "running")
        self.assertEqual(row["client_exit_signals"], [{"event": "pagehide", "elapsed_ms": 1200}])
        self.assertEqual(row["first_draft_token_ms"], 900)
        self.assertIsNone(row["feedback"])
        self.assertIsNone(row["completed_answer_ms"])
        self.assertEqual(row["question"], "Why would inventory rise?")
        ledger.finish(self.request, "completed", {}, 1900)
        vote = {"request_id": self.request, "helpful": False, "note": "I missed the date."}
        self.assertEqual(self.client.post("/api/english/feedback", json=vote).status_code, 204)
        report = read_report(self.db)
        self.assertEqual(report["summary"]["requests_with_exit_signal"], 1)
        self.assertEqual(report["summary"]["unhelpful"], 1)
        self.assertEqual(report["requests"][0]["feedback"]["note"], vote["note"])
        self.assertEqual(report["requests"][0]["completed_answer_ms"], 1900)

    def test_partial_answer_retains_question_sources_first_token_and_terminal_time(self):
        class PartialGateway:
            routes = {"knowledge_answer": SimpleNamespace(primary="default", fallbacks=())}
            profiles = {"default": SimpleNamespace(provider="openai_compatible", model="test", max_retries=0)}
            def stream(self, *args, **kwargs):
                yield "First words"
                raise RuntimeError("provider failed")

        context_id = "letter-1994-0013-0026"
        payload = {"request_id": self.request, "question": "What is value?", "entrypoint": "english_form"}
        matches = [{"context_id": context_id, "matched_paragraph_ids": []}]
        with patch.object(qa, "retrieve", return_value=(matches, {})), patch.object(qa, "get_generation_gateway", return_value=PartialGateway()):
            response = self.client.post("/api/english/ask", json=payload)
        self.assertIn('"type": "error"', response.text)
        row = read_report(self.db)["requests"][0]
        self.assertEqual(row["question"], payload["question"])
        self.assertEqual(row["server_status"], "failed_or_interrupted")
        self.assertIsNone(row["completed_answer_ms"])
        self.assertGreaterEqual(row["server_ended_ms"], row["first_draft_token_ms"])
        self.assertEqual(row["retrieved_sources"][0]["context_id"], context_id)
        self.assertEqual(row["client_exit_signals"], [])

    def test_read_only_report_and_new_writes_on_old_ledger(self):
        result = {"sources": [{"source_id": "letter", "context_id": "chapter"}],
                  "timings": {"first_token_ms": 15, "total_ms": 110}}
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TABLE requests(id TEXT PRIMARY KEY,fingerprint TEXT,status TEXT,result TEXT,created REAL)")
            db.execute("INSERT INTO requests VALUES('old','finger','completed',?,100)", (json.dumps(result),))
        self.assertEqual(read_report(self.db)["requests"], [])
        old = read_report(self.db, all_requests=True)["requests"][0]
        self.assertIsNone(old["question"])
        self.assertEqual(old["first_draft_token_ms"], 15)
        self.assertEqual(old["completed_answer_ms"], 110)
        self.assertEqual(old["retrieved_sources"], result["sources"])
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [("requests",)])
        ledger.claim(self.request, "fresh", "New question?", "english_form")
        ledger.claim(str(uuid4()), "api", "Test question?")
        self.assertEqual(len(read_report(self.db, all_requests=True)["requests"]), 3)
        self.assertEqual(len(read_report(self.db)["requests"]), 1)
        self.assertEqual(read_report(self.db, since=101, all_requests=True)["summary"]["requests"], 2)
        self.assertEqual(ledger.claim("old", "finger")["status"], "completed")
        with self.assertRaises(sqlite3.OperationalError):
            read_report(self.db.with_suffix(".missing"))
        self.assertFalse(self.db.with_suffix(".missing").exists())
