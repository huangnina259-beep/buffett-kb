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


def claim(request_id, fingerprint):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if row:
            if row["fingerprint"] != fingerprint:
                raise ValueError("This request ID belongs to a different question.")
            return dict(row)
        conn.execute("INSERT INTO requests VALUES(?,?,'running',NULL,?)", (request_id, fingerprint, time.time()))
        return None


def finish(request_id, status, result=None):
    with connection() as conn:
        conn.execute("UPDATE requests SET status=?,result=? WHERE id=?", (status, json.dumps(result) if result is not None else None, request_id))
