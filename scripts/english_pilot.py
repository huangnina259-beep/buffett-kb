"""Explicit index/status/serve commands for the bounded English pilot.

Serving never builds an index or invokes the legacy ingestion launcher.
Only --host opts into listening beyond the local machine.
"""
from pathlib import Path
import argparse
import json
import math
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def port_number(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("Port must be an integer from 1 to 65535.")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Port must be an integer from 1 to 65535.")
    return port


def runtime_settings():
    """Check effective profiles without an inference or embedding call."""
    from ai_gateway import get_generation_gateway
    from embedding_gateway import get_embedding_gateway

    gateway = get_generation_gateway()
    route = gateway.routes["knowledge_answer"]
    profile = gateway.profiles[route.primary]
    embedding = get_embedding_gateway().profile
    if profile.provider not in {"openai", "openai_compatible"} or profile.max_retries != 0 or route.fallbacks:
        raise RuntimeError("The pilot generation route must be OpenAI-compatible, with zero retries and no fallback. Check environment settings and any database/ai_settings.json override.")
    if embedding.max_retries != 0:
        raise RuntimeError("The pilot embedding profile must have zero retries. Check environment settings and any database/ai_settings.json override.")
    if not profile.api_key or not embedding.api_key:
        raise RuntimeError("Set the server-side generation and embedding API keys before starting the pilot.")
    for timeout in (profile.timeout, embedding.timeout):
        if not math.isfinite(timeout) or timeout <= 0:
            raise RuntimeError("Both model timeouts must be positive finite values.")
    try:
        call_limit = int(os.environ.get("ENGLISH_PILOT_CALL_LIMIT", "40"))
    except ValueError:
        raise RuntimeError("ENGLISH_PILOT_CALL_LIMIT must be a positive integer.")
    if call_limit < 1:
        raise RuntimeError("ENGLISH_PILOT_CALL_LIMIT must be a positive integer.")
    return {"generation_model": profile.model, "embedding_model": embedding.model, "call_limit": call_limit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["index", "serve", "status"], help="index may spend embedding calls; status and serve preflight never rebuild")
    parser.add_argument("--host", default="127.0.0.1", help="serve bind address; default: 127.0.0.1; explicitly use 0.0.0.0 for a hosted service")
    parser.add_argument("--port", type=port_number, default=None, help="serve port; --port overrides PORT, otherwise 8802")
    args = parser.parse_args()

    # Import/load after argparse so --help works offline without application
    # dependencies. Match server.py's .env precedence before checking profiles.
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
    os.environ["ENGLISH_PILOT_ENABLED"] = "true"
    os.environ["AUTO_INGEST"] = "false"
    if not args.host.strip() or any(c.isspace() for c in args.host):
        parser.error("--host must be a bind address without whitespace.")
    try:
        port = args.port if args.port is not None else port_number(os.environ.get("PORT", "8802"))
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if args.action == "index":
        from evidence_retrieval import build_index
        print(json.dumps(build_index(), indent=2))
    else:
        from evidence_retrieval import ready_index
        settings = runtime_settings()
        try:
            _, meta = ready_index()
        except Exception:
            raise RuntimeError("The existing pilot index is missing or incompatible. Run the explicit index command against this same database volume; serving will not ingest data.") from None
        if args.action == "status":
            print(json.dumps({"ready": True, "index": meta, **settings}, indent=2))
            return

        import uvicorn
        from english_app import app
        uvicorn.run(app, host=args.host, port=port, workers=1)


if __name__ == "__main__":
    main()
