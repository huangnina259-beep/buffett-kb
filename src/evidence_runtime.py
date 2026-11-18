"""Durable accounting and idempotency for the bounded English pilot.

Unknown token usage stays null. Attempts are never refunded or deleted.
This ledger is separate from historical experiments, which remain unchanged.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "database" / "english_pilot.sqlite3"


def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, stage TEXT, model TEXT, started REAL, ended REAL, status TEXT, usage TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, fingerprint TEXT, status TEXT, result TEXT, created REAL)")
    conn.execute("""CREATE TABLE IF NOT EXISTS request_metrics (
        request_id TEXT PRIMARY KEY, question TEXT, entrypoint TEXT,
        sources TEXT, first_token_ms INTEGER, ended_ms INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS request_exits (
        request_id TEXT, event TEXT, elapsed_ms INTEGER,
        PRIMARY KEY (request_id, event)
    )""")
    return conn


def reserve(stage, model):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        if count >= int(os.environ.get("ENGLISH_PILOT_CALL_LIMIT", "40")):
            raise RuntimeError("The configured pilot call limit has been reached.")
        cursor = conn.execute("INSERT INTO calls(stage,model,started,status) VALUES(?,?,?,'reserved')", (stage, model, time.time()))
        return cursor.lastrowid


def settle(call_id, status, usage=None):
    with connection() as conn:
        conn.execute("UPDATE calls SET ended=?,status=?,usage=? WHERE id=? AND status='reserved'", (time.time(), status, json.dumps(usage) if usage is not None else None, call_id))


def claim(request_id, fingerprint, question=None, entrypoint=None):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if row:
            if row["fingerprint"] != fingerprint:
                raise ValueError("This request ID belongs to a different question.")
            return dict(row)
        conn.execute("INSERT INTO requests(id,fingerprint,status,created) VALUES(?,?,'running',?)", (request_id, fingerprint, time.time()))
        conn.execute("INSERT INTO request_metrics(request_id,question,entrypoint) VALUES(?,?,?)",
                     (request_id, question, entrypoint))
        return None


def record_sources(request_id, sources):
    refs = [{key: source[key] for key in ("source_id", "context_id")} for source in sources]
    with connection() as conn:
        conn.execute("UPDATE request_metrics SET sources=? WHERE request_id=?", (json.dumps(refs), request_id))


def record_first_token(request_id, elapsed_ms):
    with connection() as conn:
        conn.execute("UPDATE request_metrics SET first_token_ms=? WHERE request_id=?", (elapsed_ms, request_id))


def record_exit(request_id, event, elapsed_ms):
    """Keep the first report of each signal. It does not control the stream."""
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT 1 FROM requests WHERE id=?", (request_id,)).fetchone():
            return False
        conn.execute("INSERT OR IGNORE INTO request_exits(request_id,event,elapsed_ms) VALUES(?,?,?)",
                     (request_id, event, elapsed_ms))
        return True


def finish(request_id, status, result=None, elapsed_ms=None):
    with connection() as conn:
        conn.execute("UPDATE requests SET status=?,result=? WHERE id=?", (status, json.dumps(result) if result is not None else None, request_id))
        conn.execute("UPDATE request_metrics SET ended_ms=? WHERE request_id=?", (elapsed_ms, request_id))
