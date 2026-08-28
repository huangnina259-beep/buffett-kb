"""ChromaDB access with embedding-profile/index consistency checks."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from embedding_gateway import EmbeddingConfigError, EmbeddingGateway, get_embedding_gateway


SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR = ROOT_DIR / "database"
DEFAULT_COLLECTION_NAME = "buffett_kb"
LEGACY_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HNSW_METADATA = {
    "hnsw:batch_size": 32,
    "hnsw:sync_threshold": 1000,
    "hnsw:num_threads": 1,
}


def collection_name() -> str:
    try:
        from ai_settings import load_saved_settings

        saved = load_saved_settings()
        if saved and saved.get("vector_collection"):
            return str(saved["vector_collection"])
    except ValueError:
        pass
    return os.environ.get("VECTOR_COLLECTION", DEFAULT_COLLECTION_NAME).strip()


def manifest_path(name: str | None = None) -> Path:
    return DB_DIR / f"{name or collection_name()}.manifest.json"


def get_client():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=DB_DIR.as_posix(),
        settings=Settings(anonymized_telemetry=False),
    )


def get_collection(*, create: bool = True):
    client = get_client()
    name = collection_name()
    try:
        return client.get_collection(name=name)
    except Exception:
        if not create:
            raise
        return client.get_or_create_collection(name=name, metadata=HNSW_METADATA)


def read_manifest(name: str | None = None) -> dict[str, Any] | None:
    path = manifest_path(name)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise EmbeddingConfigError(f"Invalid index manifest: {path}")
    return value


def build_manifest(gateway: EmbeddingGateway | None = None) -> dict[str, Any]:
    gateway = gateway or get_embedding_gateway()
    return {
        "collection": collection_name(),
        "embedding_profile": gateway.profile.name,
        "provider": gateway.profile.provider,
        "model": gateway.profile.model,
        "dimension": gateway.dimension,
        "chunk_size": 2000,
        "chunk_overlap": 400,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def write_manifest(gateway: EmbeddingGateway | None = None) -> dict[str, Any]:
    value = build_manifest(gateway)
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
    temp_path.replace(path)
    return value


def ensure_index_compatible(
    collection=None,
    gateway: EmbeddingGateway | None = None,
) -> dict[str, Any] | None:
    gateway = gateway or get_embedding_gateway()
    collection = collection or get_collection()
    manifest = read_manifest()
    count = collection.count()

    if not manifest:
        if count == 0:
            return None
        # Existing repositories predate manifests. They may only be queried when
        # the legacy local profile is explicitly selected.
        if (
            gateway.profile.provider == "local"
            and gateway.profile.model == LEGACY_LOCAL_MODEL
        ):
            return {
                "collection": collection_name(),
                "embedding_profile": "legacy_local",
                "provider": "local",
                "model": LEGACY_LOCAL_MODEL,
                "dimension": 384,
                "legacy": True,
            }
        raise EmbeddingConfigError(
            f"Collection '{collection_name()}' has {count} vectors but no embedding manifest. "
            "It cannot be queried with a cloud model. Build a new versioned collection, or "
            "explicitly select EMBEDDING_PROVIDER=local for the legacy index."
        )

    checks = {
        "embedding_profile": gateway.profile.name,
        "provider": gateway.profile.provider,
        "model": gateway.profile.model,
    }
    if gateway.dimension:
        checks["dimension"] = gateway.dimension
    mismatches = [
        f"{key}: index={manifest.get(key)!r}, configured={expected!r}"
        for key, expected in checks.items()
        if manifest.get(key) not in (None, expected)
    ]
    if mismatches:
        raise EmbeddingConfigError(
            "Embedding profile does not match the active vector index ("
            + "; ".join(mismatches)
            + "). Rebuild into a new VECTOR_COLLECTION before switching."
        )
    return manifest


def index_status() -> dict[str, Any]:
    try:
        collection = get_collection(create=False)
        count = collection.count()
    except Exception:
        count = 0
    return {
        "collection": collection_name(),
        "count": count,
        "manifest": read_manifest(),
    }
