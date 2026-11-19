"""Read recent English pilot questions and feedback privately from the local SQLite ledger."""
import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


DEFAULT_DB = Path(__file__).resolve().parents[1] / "database" / "english_pilot.sqlite3"


def utc_time(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds")


def since_timestamp(text):
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise argparse.ArgumentTypeError("Use an ISO date or timestamp, for example 2026-11-18T10:00:00Z.")
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).timestamp()


def read_report(path, limit=25, since=0, all_requests=False):
    # Open an existing volume or a snapshot without creating or migrating a ledger.
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        metrics = "request_metrics" in tables
        join = "LEFT JOIN request_metrics m ON m.request_id=r.id" if metrics else ""
        scope = "" if all_requests else ("AND m.entrypoint='english_form'" if metrics else "AND 0")
        fields = "m.question,m.entrypoint,m.sources,m.first_token_ms,m.ended_ms" if metrics else (
            "NULL AS question,NULL AS entrypoint,NULL AS sources,NULL AS first_token_ms,NULL AS ended_ms"
        )
        # Old completed rows contain their timings and source IDs inside the result.
        legacy = "CASE WHEN m.request_id IS NULL THEN r.result END" if metrics else "r.result"
        query = f"""SELECT r.id,r.created,r.status,{fields},{legacy} AS legacy
                    FROM requests r {join} WHERE r.created>=? {scope}
                    ORDER BY r.created DESC, r.id LIMIT ?"""
        records = []
        for row in db.execute(query, (since, limit)):
            old = json.loads(row["legacy"]) if row["legacy"] else {}
            timings = old.get("timings", {})
            sources = json.loads(row["sources"]) if row["sources"] is not None else None
            if sources is None and "sources" in old:
                sources = [{k: source.get(k) for k in ("source_id", "context_id")} for source in old["sources"]]
            ended_ms = row["ended_ms"] if row["ended_ms"] is not None else timings.get("total_ms")
            first_ms = row["first_token_ms"] if row["first_token_ms"] is not None else timings.get("first_token_ms")
            exits = []
            if "request_exits" in tables:
                exits = [dict(r) for r in db.execute(
                    "SELECT event,elapsed_ms FROM request_exits WHERE request_id=? ORDER BY elapsed_ms,event",
                    (row["id"],))]
            feedback = None
            if "english_feedback" in tables:
                vote = db.execute("SELECT helpful,note,updated_at FROM english_feedback WHERE request_id=?",
                                  (row["id"],)).fetchone()
                if vote:
                    feedback = {"helpful": bool(vote["helpful"]), "note": vote["note"],
                                "updated_utc": utc_time(vote["updated_at"])}
            records.append({
                "request_id": row["id"], "submitted_utc": utc_time(row["created"]),
                "question": row["question"], "entrypoint": row["entrypoint"], "server_status": row["status"],
                "first_draft_token_ms": first_ms, "completed_answer_ms": ended_ms if row["status"] == "completed" else None,
                "server_ended_ms": ended_ms, "retrieved_sources": sources,
                "client_exit_signals": exits, "feedback": feedback,
            })

    def median_ms(field):
        values = [r[field] for r in records if r[field] is not None]
        return {"observed": len(values), "median_ms": median(values) if values else None}

    return {
        "selection": {"scope": "all ledger requests" if all_requests else "English form submissions",
                      "since_utc": utc_time(since), "most_recent_limit": limit},
        "interpretation": "Server timings begin at stream start. Exit signals are best-effort client reports while waiting; "
                          "no signal means unknown. A missing vote is unknown. Form submissions may include operator tests.",
        "summary": {
            "requests": len(records), "server_statuses": dict(Counter(r["server_status"] for r in records)),
            "first_draft_token": median_ms("first_draft_token_ms"), "completed_answer": median_ms("completed_answer_ms"),
            "requests_with_exit_signal": sum(bool(r["client_exit_signals"]) for r in records),
            "helpful": sum(r["feedback"] is not None and r["feedback"]["helpful"] for r in records),
            "unhelpful": sum(r["feedback"] is not None and not r["feedback"]["helpful"] for r in records),
            "feedback_unknown": sum(r["feedback"] is None for r in records),
        },
        "requests": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="local ledger or private SQLite snapshot")
    parser.add_argument("--limit", type=int, default=25, help="most recent matching requests (1–500)")
    parser.add_argument("--since", type=since_timestamp, default=0, help="pilot start date/time (UTC unless specified)")
    parser.add_argument("--all-requests", action="store_true", help="include unlabelled API submissions and historical evaluations")
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    try:
        report = read_report(args.db, args.limit, args.since, args.all_requests)
    except sqlite3.Error as exc:
        parser.exit(1, f"Could not read the pilot ledger: {exc}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
