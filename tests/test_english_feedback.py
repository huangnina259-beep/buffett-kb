import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fastapi.testclient import TestClient

import english_app
import evidence_runtime as ledger


class EnglishFeedbackTests(unittest.TestCase):
    path = "/api/english/feedback"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db = patch.object(ledger, "DB", Path(temp.name) / "ledger.sqlite3")
        db.start()
        self.addCleanup(db.stop)
        self.client = TestClient(english_app.app)
        self.request_id = str(uuid4())
        ledger.claim(self.request_id, "original")

    def vote(self, helpful=False, note="", request_id=None, **kwargs):
        return self.client.post(self.path, json={
            "request_id": request_id or self.request_id, "helpful": helpful, "note": note,
        }, **kwargs)

    def rows(self):
        with closing(ledger.connection()) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM english_feedback")]

    def test_only_completed_requests_receive_feedback_and_status_is_private(self):
        # Existing ledgers already contain requests from before feedback was added.
        for status, request_id in (("running", self.request_id), ("unknown", str(uuid4())),
                                   ("failed_or_interrupted", self.request_id)):
            with self.subTest(status=status):
                if status == "failed_or_interrupted":
                    ledger.finish(self.request_id, status)
                response = self.vote(request_id=request_id)
                self.assertEqual((response.status_code, response.content), (204, b""))
                self.assertEqual(self.rows(), [])
        self.assertEqual(self.client.get(self.path).status_code, 405)
        self.assertEqual(self.client.get(f"{self.path}/{self.request_id}").status_code, 404)

    def test_vote_retry_is_idempotent_and_correction_clears_old_note(self):
        ledger.finish(self.request_id, "completed", {"answer": "pilot"})
        with patch("english_feedback.time.time", return_value=10):
            result = self.vote(note="  Too general. ")
        self.assertEqual((result.status_code, result.content), (204, b""))
        original = self.rows()
        self.assertEqual(original, [{"request_id": self.request_id, "helpful": 0,
                                    "note": "Too general.", "updated_at": 10}])
        self.vote(note="Too general.")
        self.assertEqual(self.rows(), original)
        self.vote(helpful=True, note="stale text")
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["helpful"], 1)
        self.assertIsNone(self.rows()[0]["note"])

    def test_pilot_accepts_only_same_origin_browser_writes(self):
        ledger.finish(self.request_id, "completed", {})
        for headers in ({"Origin": "https://testserver"}, {"Origin": "http://another.example"},
                        {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.vote(headers=headers).status_code, 403)
        response = self.vote(headers={"Origin": "http://testserver:80", "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(self.rows()), 1)

    def test_all_writes_share_the_configured_https_origin_after_railway_tls_termination(self):
        domain = "pilot.example"
        replay = {"status": "completed", "result": '{"answer":"example","sources":[]}'}
        cases = [
            ("ask", {"question": "Scope?"}, 200),
            ("left", {"event": "stop", "elapsed_ms": 100}, 200),
            ("feedback", {"helpful": True}, 204),
        ]
        with patch.dict("os.environ", {"RAILWAY_PUBLIC_DOMAIN": domain}), patch("english_qa.claim", return_value=replay):
            for route, payload, success in cases:
                url = "/api/english/" + route
                data = {"request_id": self.request_id, **payload}
                with self.subTest(route=route):
                    accepted = {"host": domain, "origin": "https://" + domain}
                    self.assertEqual(self.client.post(url, json=data, headers=accepted).status_code, success)
                    for headers in [
                        {**accepted, "origin": "http://" + domain},
                        {**accepted, "origin": "https://" + domain + ":8000"},
                        {**accepted, "host": "private.internal", "x-forwarded-host": domain},
                        {"origin": "https://testserver", "x-forwarded-proto": "https"},
                    ]:
                        self.assertEqual(self.client.post(url, json=data, headers=headers).status_code, 403)

    def test_feedback_is_available_on_the_shared_opt_in_english_router(self):
        from fastapi import FastAPI
        from english_qa import router
        mounted = FastAPI()
        mounted.include_router(router)
        response = TestClient(mounted).post(self.path, json={"request_id": self.request_id, "helpful": True})
        self.assertEqual(response.status_code, 204)

    def test_invalid_rating_or_oversized_note_cannot_replace_existing_vote(self):
        ledger.finish(self.request_id, "completed", {})
        self.vote(helpful=True)
        for response in (self.vote(helpful="no"), self.vote(note="x" * 501)):
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.rows()[0]["helpful"], 1)


if __name__ == "__main__":
    unittest.main()
