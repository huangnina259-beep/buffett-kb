"""Write-only reader feedback for completed English pilot answers."""
from __future__ import annotations

import os
import time
from contextlib import closing
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, StrictBool

from evidence_runtime import connection

router = APIRouter()


def require_same_origin(request: Request):
    forbidden = HTTPException(403, "This pilot accepts same-origin requests only.")
    if request.headers.get("sec-fetch-site") in {"same-site", "cross-site"}:
        raise forbidden
    origin = request.headers.get("origin")
    if origin is None:
        return  # Non-browser clients may omit Origin.
    try:
        claimed = urlsplit(origin)
        actual = request.url
        scheme = actual.scheme
        public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip().lower()
        # Railway can terminate HTTPS before the ASGI hop. Only the configured
        # public Host gets this canonical scheme; forwarded headers are unused.
        if public_domain and actual.hostname == public_domain and actual.port in (None, 443):
            scheme = "https"
        default_ports = {"http": 80, "https": 443}
        if (claimed.scheme == scheme and scheme in default_ports and claimed.hostname == actual.hostname
                and claimed.username is None and not (claimed.path or claimed.query or claimed.fragment)):
            default = default_ports[scheme]
            claimed_port = claimed.port if claimed.port is not None else default
            actual_port = actual.port if actual.port is not None else default
            if claimed_port == actual_port:
                return
    except ValueError:
        pass
    raise forbidden


class Feedback(BaseModel):
    request_id: UUID
    helpful: StrictBool
    note: str = Field(default="", max_length=500)


@router.post("/api/english/feedback", status_code=204)
def save_feedback(payload: Feedback, request: Request):
    require_same_origin(request)
    note = None if payload.helpful else payload.note.strip() or None
    with closing(connection()) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS english_feedback (
            request_id TEXT PRIMARY KEY, helpful INTEGER NOT NULL CHECK(helpful IN (0, 1)),
            note TEXT, updated_at REAL NOT NULL)""")
        # One atomic statement also prevents orphan or unfinished-answer votes.
        # The public response does not disclose whether this ID exists.
        conn.execute("""
            INSERT INTO english_feedback (request_id, helpful, note, updated_at)
            SELECT id, ?, ?, ? FROM requests WHERE id = ? AND status = 'completed'
            ON CONFLICT (request_id) DO UPDATE SET
                helpful = excluded.helpful, note = excluded.note, updated_at = excluded.updated_at
            WHERE english_feedback.helpful != excluded.helpful OR english_feedback.note IS NOT excluded.note
        """, (int(payload.helpful), note, time.time(), str(payload.request_id)))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
