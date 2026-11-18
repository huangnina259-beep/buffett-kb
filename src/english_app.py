"""Minimal HTTP surface for the bounded original-source English pilot.

Use the existing router and gateways without mounting the legacy application.
This module adds no authentication and performs no model calls at import time.
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from english_qa import page, router
from evidence_retrieval import ready_index


app = FastAPI(
    title="Buffett original-source English pilot",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router)
app.add_api_route("/", page, methods=["GET"], response_class=HTMLResponse)


@app.get("/health")
def health():
    """Report local index readiness, never imply a paid model was tested."""
    try:
        _, metadata = ready_index()
    except Exception:
        return JSONResponse(
            {"status": "not_ready", "index_ready": False,
             "scope": "Pilot source index only; provider access and answer quality are not tested."},
            status_code=503,
        )
    return {
        "status": "ready",
        "index_ready": True,
        "source_contexts": metadata.get("contexts"),
        "scope": "Pilot source index only; provider access and answer quality are not tested.",
    }
