"""Exercise a deployed English pilot over HTTP(S). Two synthetic questions use up to six provider calls.

Supply the pilot origin with --url. If a shared password is needed, set
ENGLISH_BETA_PASSWORD in the client environment. Synthetic API submissions are
excluded from the private review command's default browser-form selection.
"""
import argparse
import base64
import http.client
import ipaddress
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit
from uuid import uuid4


def pilot_url(value):
    try:
        url = urlsplit(value)
        host = url.hostname
        port = url.port
        local = host == "localhost"
        try:
            local |= ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if (host and (port is None or port > 0) and url.username is None and url.password is None
                and url.path in ("", "/") and not url.query and not url.fragment
                and (url.scheme == "https" or (url.scheme == "http" and local))):
            return url
    except (TypeError, ValueError):
        pass
    raise argparse.ArgumentTypeError("Use an HTTPS origin or an HTTP loopback origin. Omit credentials and paths.")


class Pilot:
    def __init__(self, url):
        self.url = url
        self.origin = f"{url.scheme}://{url.netloc}"
        self.headers = {"Origin": self.origin}
        password = os.environ.get("ENGLISH_BETA_PASSWORD")
        if password:
            token = base64.b64encode(("reader:" + password).encode()).decode("ascii")
            self.headers["Authorization"] = "Basic " + token

    @contextmanager
    def request(self, path, payload=None, expected=200):
        # An origin-bound connection never follows redirects carrying the shared password.
        factory = http.client.HTTPSConnection if self.url.scheme == "https" else http.client.HTTPConnection
        connection = factory(self.url.hostname, self.url.port, timeout=210)
        try:
            headers = dict(self.headers)
            body = None
            if payload is not None:
                body = json.dumps(payload).encode()
                headers["Content-Type"] = "application/json"
            connection.request("POST" if body is not None else "GET", path, body=body, headers=headers)
            response = connection.getresponse()
            if response.status != expected:
                raise RuntimeError(f"{path} returned HTTP {response.status} (expected {expected}).")
            yield response
        finally:
            connection.close()

    def ask(self, question, history, result):
        request_id = str(uuid4())
        started = time.monotonic()
        result.update(request_id=request_id, history_turns=len(history))
        sources = {}
        with self.request("/api/english/ask", {"question": question, "history": history, "request_id": request_id}) as response:
            if response.headers.get_content_type() != "text/event-stream":
                raise RuntimeError("Ask did not return an event stream.")
            for line in response:
                if not line.startswith(b"data: "):
                    continue
                event = json.loads(line[6:])
                elapsed = round(1000 * (time.monotonic() - started))
                if event["type"] == "sources":
                    sources = {s["id"]: s["context_id"] for s in event["sources"]}
                elif event["type"] == "token" and event.get("text"):
                    result.setdefault("client_first_draft_ms", elapsed)
                elif event["type"] == "error":
                    raise RuntimeError("The answer stream reported an error.")
                elif event["type"] == "done":
                    answer = event["answer"]
                    refs = list(dict.fromkeys(int(n) for n in re.findall(r"\[(\d+)\]", answer)))
                    if not answer.strip() or "client_first_draft_ms" not in result:
                        raise RuntimeError("The answer stream lacked draft or final text.")
                    if not refs or any(ref not in sources for ref in refs):
                        raise RuntimeError("The final answer had missing or unresolved citations.")
                    result.update(client_completed_ms=elapsed, model=event["model"], prompt_version=event["prompt_version"],
                                  answer_characters=len(answer), retrieved_contexts=len(sources), cited_contexts=len(refs),
                                  reported_usage=event.get("usage"), reference_check=event["validation"]["status"])
                    return answer, sources[refs[0]]
        raise RuntimeError("The stream closed before the final answer.")


def run(pilot, result):
    with pilot.request("/") as response:
        html = response.read().decode()
        if not all(f'id="{element}"' in html for element in ("question-form", "feedback-yes", "feedback-no", "source-dialog")):
            raise RuntimeError("The homepage is missing a required reader control.")
        result["homepage_http"] = response.status
    with pilot.request("/health") as response:
        health = json.load(response)
        if health.get("index_ready") is not True:
            raise RuntimeError("The pilot index is not ready.")
        result["indexed_contexts"] = health["source_contexts"]
    history = []
    for question, vote in [("How does Buffett define owner earnings?", True),
                           ("How does that calculation handle extra inventory needed to maintain sales?", False)]:
        observation = {}
        result["questions"].append(observation)
        answer, context_id = pilot.ask(question, history, observation)
        with pilot.request("/api/english/sources/" + quote(context_id, safe="")) as response:
            source = json.load(response)
            if source.get("context_id") != context_id or not any(
                (p.get("reading_text") or p.get("text") or "").strip() for p in source.get("paragraphs", [])):
                raise RuntimeError("A cited source did not return readable original paragraphs.")
            observation.update(opened_cited_context=context_id, source_paragraphs=len(source["paragraphs"]))
        feedback = {"request_id": observation["request_id"], "helpful": vote}
        if not vote:
            feedback["note"] = "Synthetic smoke test."
        with pilot.request("/api/english/feedback", feedback, expected=204) as response:
            observation.update(synthetic_vote=vote, feedback_http=response.status)
        history = [{"role": "user", "content": question}, {"role": "assistant", "content": answer[:12000]}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, type=pilot_url, help="pilot origin")
    args = parser.parse_args()
    pilot = Pilot(args.url)
    result = {"started_utc": datetime.now(timezone.utc).isoformat(), "origin": pilot.origin,
              "synthetic": True, "questions": [], "passed": False}
    try:
        run(pilot, result)
        result["passed"] = True
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, http.client.HTTPException) as exc:
        # Only our fixed diagnostic messages are safe to include in the report.
        result["error"] = str(exc) if type(exc) is RuntimeError else type(exc).__name__
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
