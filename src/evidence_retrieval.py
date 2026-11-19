"""Hybrid child-passage retrieval with complete, immutable parent contexts.

Uses buffett-kb's embedding gateway, Chroma client, and reciprocal-rank fusion.
This collection never queries the legacy mixed-author Markdown corpus.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from functools import lru_cache
from threading import RLock
from pathlib import Path

from embedding_gateway import get_embedding_gateway
from lexical_search import fuse_evidence
from source_contexts import load_contexts, search_units
from vector_store import get_client
from evidence_runtime import reserve, settle

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = "buffett_english_contexts_v1"
MANIFEST = ROOT / "database" / (COLLECTION + ".json")
LOCK = RLock()
STOP = set("the and what how does with that this for from are why can could would should about into have has its than just when which who your you me it is to of a an i my if in on at be do as or their they them really give get".split())


def corpus_hash():
    return hashlib.sha256(json.dumps(load_contexts(), ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build_index():
    gateway = get_embedding_gateway()
    if gateway.profile.max_retries != 0:
        raise RuntimeError("The pilot embedding route must disable automatic retries.")
    units = search_units()
    signature = {"corpus_sha256": corpus_hash(), "model": gateway.profile.model, "provider": gateway.profile.provider, "base_url": gateway.profile.base_url, "units": len(units)}
    client = get_client()
    if MANIFEST.exists():
        old = json.loads(MANIFEST.read_text())
        if all(old.get(k) == v for k, v in signature.items()):
            collection = client.get_collection(COLLECTION)
            if collection.count() == len(units):
                return old
        raise RuntimeError("The existing pilot index is incompatible. Use an explicitly versioned collection; do not overwrite it.")
    collection = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine", "hnsw:num_threads": 1})
    batch_size = gateway.profile.batch_size
    for start in range(0, len(units), batch_size):
        batch = units[start:start + batch_size]
        call = reserve("index_embedding", gateway.profile.model)
        try:
            vectors = gateway.embed_documents([u["text"] for u in batch])
            collection.upsert(ids=[u["id"] for u in batch], embeddings=vectors, documents=[u["text"] for u in batch], metadatas=[{"context_id": u["context_id"], "source_file": u["context_id"], "paragraph_ids": json.dumps(u["paragraph_ids"])} for u in batch])
            settle(call, "completed")
        except Exception:
            settle(call, "failed")
            raise
    signature.update({"dimension": gateway.dimension, "chunking": "whole-paragraph children; complete parent expansion", "contexts": len(load_contexts())})
    MANIFEST.write_text(json.dumps(signature, indent=2))
    return signature


def ready_index():
    if not MANIFEST.exists():
        raise RuntimeError("The pilot source index has not been built.")
    meta = json.loads(MANIFEST.read_text())
    gateway = get_embedding_gateway()
    if meta.get("corpus_sha256") != corpus_hash() or meta.get("model") != gateway.profile.model or meta.get("base_url") != gateway.profile.base_url:
        raise RuntimeError("The pilot source index does not match the active sources or embedding model.")
    collection = get_client().get_collection(COLLECTION)
    if collection.count() != meta["units"]:
        raise RuntimeError("The pilot source index is incomplete.")
    return collection, meta


@lru_cache(maxsize=1)
def lexical_index():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE VIRTUAL TABLE passages USING fts5(body,metadata UNINDEXED, tokenize='porter unicode61')")
    for unit in search_units():
        metadata = {"context_id": unit["context_id"], "source_file": unit["context_id"], "paragraph_ids": json.dumps(unit["paragraph_ids"])}
        conn.execute("INSERT INTO passages VALUES(?,?)", (unit["text"], json.dumps(metadata)))
    conn.commit()
    return conn


def lexical(query):
    words = list(dict.fromkeys(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]{1,}", query) if w.lower() not in STOP))[:32]
    rows = []
    if words:
        match = " OR ".join('"' + w + '"' for w in words)
        with LOCK:
            rows = lexical_index().execute("SELECT body,metadata FROM passages WHERE passages MATCH ? ORDER BY bm25(passages) LIMIT 30", (match,)).fetchall()
    return {"documents": [[r[0] for r in rows]], "metadatas": [[json.loads(r[1]) for r in rows]]}


FOLLOWUP_REFERENCE = re.compile(
    r"\b(it|its|he|his|him|she|her|they|their|them|this|these|those)\b"
    r"|\bthat\s+(?:mean|relate|work|change|compare|apply|case|example|method|approach|business|one)\b"
    r"|\b(?:do|does|did|is|was|about|by|from)\s+that\b|\bthat[?.!]?$"
    r"|^(?:and\b|what about\b|why[?.!]*$|can you (?:explain|elaborate|give an example)\b)",
    re.IGNORECASE,
)


def retrieval_question(question, history):
    """Carry the topic through linked follow-ups without indexing prior answer text."""
    if not FOLLOWUP_REFERENCE.search(question.strip()):
        return question
    earlier = []
    for turn in reversed(history or []):
        if turn["role"] != "user":
            continue
        previous = turn["content"].strip()
        earlier.append(previous[:600])
        if not FOLLOWUP_REFERENCE.search(previous):
            break
    return "\n".join([question, *reversed(earlier)])


def select_contexts(groups, contexts, selected_context_id=None):
    """Keep the clicked original first, then fill the existing budget in search rank order."""
    ranked = sorted(groups, key=lambda cid: groups[cid]["score"], reverse=True)
    if selected_context_id is not None:
        ranked = [selected_context_id, *(cid for cid in ranked if cid != selected_context_id)]
    chosen, chars = [], 0
    for cid in ranked:
        size = sum(len(p.get("reading_text") or p.get("text", "")) for p in contexts[cid]["paragraphs"])
        if chars + size > 50000:
            if cid == selected_context_id:
                raise ValueError("The selected original exceeds the context budget.")
            continue
        detail = groups.get(cid, {"hits": [], "score": None})
        chosen.append({"context_id": cid, "matched_paragraph_ids": list(dict.fromkeys(detail["hits"])), "rank_score": detail["score"]})
        chars += size
        if len(chosen) >= 5:
            break
    return chosen, chars


def retrieve(question, history=None, selected_context_id=None):
    collection, meta = ready_index()
    query = retrieval_question(question, history)
    gateway = get_embedding_gateway()
    if gateway.profile.max_retries != 0:
        raise RuntimeError("The pilot embedding route must disable automatic retries.")
    call = reserve("query_embedding", gateway.profile.model)
    try:
        # Qwen's documented query instruction; document embeddings stay plain.
        embedding_query = ("Instruct: Given an investing question, retrieve original Berkshire passages that directly answer it.\nQuery: " + query) if "qwen3-embedding" in gateway.profile.model.lower() else query
        vector = gateway.embed_query(embedding_query)
        if len(vector) != meta["dimension"]:
            raise RuntimeError("Query embedding dimension does not match the index.")
        settle(call, "completed")
    except Exception:
        settle(call, "failed")
        raise
    semantic = collection.query(query_embeddings=[vector], n_results=min(30, collection.count()))
    text_results = lexical(query)
    fused = fuse_evidence(semantic, text_results, limit=24)
    groups = {}
    for rank, (metadata, distance) in enumerate(zip(fused["metadatas"][0], fused["distances"][0])):
        cid = metadata["context_id"]
        group = groups.setdefault(cid, {"score": 0, "hits": []})
        # Use the best child score, so long parents do not win merely by having
        # two moderately related windows in the fused candidate list.
        group["score"] = max(group["score"], 1 - distance)
        group["hits"].extend(json.loads(metadata["paragraph_ids"]))
    contexts = load_contexts()
    chosen, chars = select_contexts(groups, contexts, selected_context_id)
    return chosen, {"mode": "semantic + FTS5 + rank fusion + complete context expansion", "context_count": len(contexts), "selected_characters": chars, "best_cosine_distance": semantic["distances"][0][0] if semantic["distances"][0] else None}
