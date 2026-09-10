"""Local full-text evidence lookup; no model calls or re-embedding required."""
import json
import re
import sqlite3
from functools import lru_cache
from threading import RLock
from pathlib import Path

_lock = RLock()

@lru_cache(maxsize=1)
def _index():
    from ingest_md import MD_DIR, chunk_text, get_file_metadata
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    connection.execute('CREATE VIRTUAL TABLE evidence USING fts5(body, metadata UNINDEXED)')
    for path in sorted(MD_DIR.glob('*.md')):
        metadata, content = get_file_metadata(path, path.read_text(encoding='utf-8'))
        for chunk in chunk_text(content):
            if useful_passage(chunk):
                connection.execute('INSERT INTO evidence(body,metadata) VALUES (?,?)',
                                   (chunk, json.dumps(metadata, ensure_ascii=False)))
    connection.commit()
    return connection


def useful_passage(text):
    return len(re.findall(r'[A-Za-z0-9\u4e00-\u9fff]', text)) >= 80


def search_evidence(query, limit=24):
    # English hints match the English primary sources; Chinese-only questions
    # continue through multilingual semantic retrieval instead.
    words = [w.lower() for w in re.findall(r'[A-Za-z][A-Za-z-]{2,}', query)]
    stop = {'the','and','what','how','does','with','that','this','for','from','are','why'}
    words = list(dict.fromkeys(w for w in words if w not in stop))[:16]
    if not words:
        return {'documents':[[]], 'metadatas':[[]], 'distances':[[]]}
    match = ' OR '.join('"'+w+'"' for w in words)
    with _lock:
        rows = _index().execute('SELECT body,metadata,bm25(evidence) FROM evidence WHERE evidence MATCH ? ORDER BY bm25(evidence) LIMIT ?', (match,limit)).fetchall()
    return {'documents':[[r[0] for r in rows]], 'metadatas':[[json.loads(r[1]) for r in rows]], 'distances':[[i/100 for i in range(len(rows))]]}


def fuse_evidence(semantic, lexical, limit):
    candidates={}
    for weight, result in [(1.0,semantic),(1.0,lexical)]:
        for rank,(body,meta) in enumerate(zip(result['documents'][0], result['metadatas'][0])):
            if not useful_passage(body):
                continue
            key=(meta.get('source_file',''),body)
            entry=candidates.setdefault(key,[0,body,meta])
            entry[0] += weight/(30+rank+1)
    ranked=sorted(candidates.values(),key=lambda row:row[0],reverse=True)
    chosen=[]; counts={}
    for score,body,meta in ranked:
        source=meta.get('source_file') or meta.get('source_label','')
        if counts.get(source,0)>=2:
            continue
        counts[source]=counts.get(source,0)+1
        chosen.append((score,body,meta))
        if len(chosen)>=limit:
            break
    return {'documents':[[r[1] for r in chosen]],'metadatas':[[r[2] for r in chosen]],'distances':[[1-r[0] for r in chosen]]}
