"""Explicit live checks. Each case spends one embedding and one writer call, plus one review call
when ENGLISH_PILOT_VERIFY is enabled.

Only named cases run. Results contain the actual answer, sources, timings and
provider-reported usage. Completion and citation checks are not semantic passes.
"""
import argparse
import json
import time
import urllib.request
import uuid
from pathlib import Path

CASES = {
    "V0": "how to evaluate a stock",
    "V1": "How would I work out what a company is worth before deciding whether its shares are a bargain?",
    "V2": "If I'm buying a small piece of a business, how do I judge a sensible price without just relying on its P/E ratio?",
    "V3": "How do I go from estimating what the whole business can pay its owners to deciding whether one share is cheap?",
    "O1": "What makes reported profit different from cash an owner can actually take out of a business?",
    "O2": "A business must put more cash into inventory just to keep sales volume unchanged. In Buffett's owner-earnings calculation, does that raise or reduce the cash available to owners?",
    "C1": "How can I tell whether I really understand a business, rather than just know its products?",
    "A1": "Using Buffett's valuation principles, is Apple cheap enough for me to buy today?",
    "N1": "Can you give me a reliable sourdough recipe for a first loaf?",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="+", choices=list(CASES))
    parser.add_argument("--url", default="http://127.0.0.1:8802")
    parser.add_argument("--output", type=Path, default=Path("database/evaluation"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for case in args.cases:
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        result = {"case": case, "question": CASES[case], "request_id": request_id, "events": []}
        request = urllib.request.Request(args.url.rstrip("/") + "/api/english/ask", data=json.dumps({"question": CASES[case], "request_id": request_id}).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=200) as response:
                for line in response:
                    if line.startswith(b"data: "):
                        event = json.loads(line[6:])
                        event["elapsed_ms"] = round((time.monotonic() - started) * 1000)
                        result["events"].append(event)
        except BaseException as exc:
            result["events"].append({"type": "client_error", "class": type(exc).__name__})
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
        finally:
            result["client_total_ms"] = round((time.monotonic() - started) * 1000)
            (args.output / f"{case}-{request_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        completed = any(e["type"] == "done" for e in result["events"])
        print(case, "completed" if completed else "failed", result["client_total_ms"], "ms", flush=True)


if __name__ == "__main__":
    main()
