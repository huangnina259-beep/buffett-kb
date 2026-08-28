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


def database_exists() -> bool:
    """Check the configured collection, not merely the shared Chroma file."""
    try:
        src_dir = Path(__file__).parent / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        from embedding_gateway import get_embedding_gateway
        from vector_store import ensure_index_compatible, get_collection

        collection = get_collection(create=False)
        ensure_index_compatible(collection, get_embedding_gateway())
        return collection.count() > 0
    except Exception as exc:
        logging.warning("[start] Configured vector index is not ready: %s", exc)
        return False


def _run_ingest():
    logging.info("[start] Database not found — running ingest_md.py in background...")
    result = subprocess.run(
        [sys.executable, "src/ingest_md.py"],
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    if result.returncode != 0:
        logging.error("[start] ingest_md.py failed (exit %s) — Q&A will not work until redeployed", result.returncode)
    else:
        logging.info("[start] Background ingest complete — Q&A is now ready.")


if __name__ == "__main__":
    DB_DIR.mkdir(exist_ok=True)

    if not database_exists():
        auto_ingest = os.environ.get("AUTO_INGEST", "false").lower() in {
            "1", "true", "yes", "on"
        }
        if auto_ingest:
            # Explicit opt-in avoids an unexpected paid cloud embedding job.
            t = threading.Thread(target=_run_ingest, daemon=True)
            t.start()
        else:
            logging.warning(
                "[start] Vector index is not ready. Automatic ingestion is disabled; "
                "run src/ingest_md.py manually after testing the embedding model, or set "
                "AUTO_INGEST=true to opt in."
            )
    else:
        logging.info("[start] Database found, skipping ingest.")

    port = os.environ.get("PORT", "8000")
    logging.info("[start] Starting server on port %s...", port)
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn", "server:app",
        "--host", "0.0.0.0",
        "--port", port,
    ])
