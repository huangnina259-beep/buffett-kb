"""
Startup script for Railway deployment.
- Starts uvicorn immediately so Railway healthcheck passes.
- If the ChromaDB database is empty/missing, runs ingest_md.py in a background
  thread so the server is available right away.
- Q&A endpoints return a friendly "warming up" message while ingest is running.
"""
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DB_DIR   = Path(__file__).parent / "database"
DB_FILE  = DB_DIR / "chroma.sqlite3"


def database_exists() -> bool:
    return DB_FILE.exists() and DB_FILE.stat().st_size > 1_000_000  # >1 MB means populated


def _run_ingest():
    logging.info("[start] Database not found — running ingest_md.py in background...")
    result = subprocess.run(
        [sys.executable, "src/ingest_md.py"],
        cwd=Path(__file__).parent,
    )
    if result.returncode != 0:
        logging.error("[start] ingest_md.py failed (exit %s) — Q&A will not work until redeployed", result.returncode)
    else:
        logging.info("[start] Background ingest complete — Q&A is now ready.")


if __name__ == "__main__":
    DB_DIR.mkdir(exist_ok=True)

    if not database_exists():
        # Start ingest in background so uvicorn launches immediately
        t = threading.Thread(target=_run_ingest, daemon=True)
        t.start()
    else:
        logging.info("[start] Database found, skipping ingest.")

    port = os.environ.get("PORT", "8000")
    logging.info("[start] Starting server on port %s...", port)
    os.execvp("uvicorn", [
        "uvicorn", "server:app",
        "--host", "0.0.0.0",
        "--port", port,
    ])
