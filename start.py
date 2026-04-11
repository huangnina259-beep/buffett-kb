"""
Startup script for Railway deployment.
- If the ChromaDB database is empty/missing, runs ingest_md.py first.
- Then starts the FastAPI server.
"""
import os
import subprocess
import sys
from pathlib import Path

DB_DIR   = Path(__file__).parent / "database"
DB_FILE  = DB_DIR / "chroma.sqlite3"

def database_exists():
    return DB_FILE.exists() and DB_FILE.stat().st_size > 1_000_000  # >1MB means populated

def run_ingest():
    print("[start] Database not found — running ingest_md.py...")
    result = subprocess.run(
        [sys.executable, "src/ingest_md.py"],
        cwd=Path(__file__).parent,
    )
    if result.returncode != 0:
        print("[start] ERROR: ingest failed, aborting.")
        sys.exit(1)
    print("[start] Ingest complete.")

def start_server():
    port = os.environ.get("PORT", "8000")
    print(f"[start] Starting server on port {port}...")
    os.execvp("uvicorn", [
        "uvicorn", "server:app",
        "--host", "0.0.0.0",
        "--port", port,
    ])

if __name__ == "__main__":
    DB_DIR.mkdir(exist_ok=True)
    if not database_exists():
        run_ingest()
    else:
        print("[start] Database found, skipping ingest.")
    start_server()
