"""
Ingest all Buffett documents into ChromaDB from the Cleaned Markdown Knowledge Base.
Parses YAML frontmatter for precise metadata.
Uses Langchain's RecursiveCharacterTextSplitter to avoid MemoryErrors.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from embedding_gateway import get_embedding_gateway
from vector_store import collection_name, ensure_index_compatible, get_collection, write_manifest

# ── paths ─────────────────────────────────────────────────────────────────────
SRC_DIR  = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR   = ROOT_DIR / "database"
MD_DIR   = ROOT_DIR / "data" / "clean_mds"

# ── constants ─────────────────────────────────────────────────────────────────
CHUNK_SIZE      = 2000   # chars ≈ 500-600 tokens
CHUNK_OVERLAP   = 400    # chars ≈ 100 tokens
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    is_separator_regex=False,
)


def ingestion_summary_path() -> Path:
    """Keep resumable progress isolated per vector collection/version."""
    return DB_DIR / f"ingestion_summary.{collection_name()}.json"


def write_ingestion_summary(path: Path, summary: dict) -> None:
    """Checkpoint progress atomically so an interrupted paid job can resume."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    temporary.replace(path)

def chunk_text(text: str) -> list[str]:
    return text_splitter.split_text(text)

def parse_frontmatter(text: str):
    meta = {}
    content = text
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) >= 3:
            header = parts[1]
            content = parts[2].strip()
            for line in header.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v.startswith("[") and v.endswith("]"):
                        v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                    elif v.isdigit():
                        v = int(v)
                    meta[k] = v
    return meta, content

def get_file_metadata(file_path: Path, text: str):
    """Get metadata from frontmatter or filename."""
    name = file_path.name
    meta_dict, content = parse_frontmatter(text)
    
    label = meta_dict.get("title", name.replace(".md", ""))
    year = meta_dict.get("year", 0)
    doc_type = meta_dict.get("doc_type", "document")

    # Author: frontmatter has a list, ChromaDB needs a string
    raw_author = meta_dict.get("author", [])
    if isinstance(raw_author, list):
        author = ", ".join(raw_author) if raw_author else ""
    else:
        author = str(raw_author).strip()

    # Fallback: infer author from filename / doc_type
    if not author:
        n = name.lower()
        if "buffett" in n or "shareholder_letter" in doc_type or "letter" in n:
            author = "Warren Buffett"
        elif "munger" in n or "poor_charlie" in n or "almanack" in n:
            author = "Charlie Munger"
        elif "howard_marks" in n or "marks" in n:
            author = "Howard Marks"
        elif "li_lu" in n or "lilu" in n:
            author = "Li Lu"

    # Fallback to filename guessing if metadata is missing
    if not year:
        year_match = re.search(r"(19|20)\d{2}", name)
        if year_match:
            year = int(year_match.group(0))

    if doc_type == "document":
        if "meeting" in name.lower() or "session" in name.lower() or "transcript" in name.lower():
            doc_type = "meeting_transcript"
        elif "letter" in name.lower():
            doc_type = "shareholder_letter"
        elif "munger" in name.lower() or "poor charlie" in name.lower() or "speech" in name.lower():
            doc_type = "munger_wisdom"
        elif "valuation" in name.lower():
            doc_type = "valuation_guide"

    # Language detection based on filename
    language = "en"
    if "_CN.md" in name or any('\u4e00' <= char <= '\u9fff' for char in name):
        language = "zh"
    elif "_EN.md" in name:
        language = "en"

    return {
        "source_label": label,
        "year": year,
        "doc_type": doc_type,
        "author": author,
        "source_file": name,
        "language": language
    }, content

# ── Main Ingestion ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Reprocess all files")
    parser.add_argument("--start", type=int, default=None, help="Start index (inclusive) for batch processing")
    parser.add_argument("--end", type=int, default=None, help="End index (exclusive) for batch processing")
    args = parser.parse_args()

    print("🚀 Initialising ChromaDB...")
    embedding_gateway = get_embedding_gateway()
    collection = get_collection()
    ensure_index_compatible(collection, embedding_gateway)
    print(
        f"Embedding profile: {embedding_gateway.profile.name} "
        f"({embedding_gateway.profile.provider}/{embedding_gateway.profile.model})"
    )

    summary_path = ingestion_summary_path()
    summary = {"files": {}, "total_chunks": 0}
    if summary_path.exists() and not args.force:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
    processed_files = set(summary.get("files", {}).keys())

    if not MD_DIR.exists():
        print(f"❌ Clean Markdown directory not found: {MD_DIR}")
        return

    all_mds = sorted(MD_DIR.glob("*.md"))
    total_files = len(all_mds)

    start = args.start if args.start is not None else 0
    end = args.end if args.end is not None else total_files
    all_mds = all_mds[start:end]

    print(f"Found {total_files} Markdown files in {MD_DIR}")
    print(f"Processing batch [{start}:{end}] → {len(all_mds)} files")

    total_chunks_added = 0
    file_stats = {}

    for md_path in all_mds:
        if md_path.name in processed_files:
            continue

        print(f"📄 Processing {md_path.name}...")
        try:
            with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e:
            print(f"❌ Error reading {md_path.name}: {e}")
            continue
            
        if not raw_text.strip():
            continue

        # Extract metadata and clean text
        metadata, text = get_file_metadata(md_path, raw_text)

        try:
            chunks = chunk_text(text)
        except Exception as e:
            print(f"❌ Error chunking {md_path.name}: {e}")
            continue

        if not chunks:
            continue
        
        # Keep batches modest on Windows: larger upserts can crash the native
        # Chroma HNSW extension instead of raising a Python exception.
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i+batch_size]
            ids = [f"{md_path.name}_{i+j}" for j in range(len(batch_chunks))]
            metas = []
            for j in range(len(batch_chunks)):
                m = metadata.copy()
                m["chunk_index"] = i + j
                m["total_chunks"] = len(chunks)
                # Keep snippet empty here,rag.py format_context handles formatting
                metas.append(m)
                
            try:
                if not args.force:
                    existing = set(collection.get(ids=ids, include=[])["ids"])
                    missing = [j for j, identifier in enumerate(ids) if identifier not in existing]
                    if not missing:
                        continue
                    ids = [ids[j] for j in missing]
                    metas = [metas[j] for j in missing]
                    batch_chunks = [batch_chunks[j] for j in missing]
                embeddings = embedding_gateway.embed_documents(batch_chunks)
                collection.upsert(
                    ids=ids,
                    documents=batch_chunks,
                    metadatas=metas,
                    embeddings=embeddings,
                )
                write_manifest(embedding_gateway)
            except Exception as e:
                print(f"❌ Error adding batch to ChromaDB for {md_path.name}: {e}")
                raise

        print(f"✅ Ingested {len(chunks)} chunks from {md_path.name}")
        total_chunks_added += len(chunks)
        file_stats[md_path.name] = {
            "chunks": len(chunks),
            "ingested_at": datetime.now().isoformat()
        }

        # Persist after every completed source file. IDs are deterministic, so
        # retrying a partially completed file safely upserts its existing rows.
        summary["files"][md_path.name] = file_stats[md_path.name]
        summary["total_chunks"] = int(summary.get("total_chunks", 0)) + len(chunks)
        write_ingestion_summary(summary_path, summary)

    # Also create a summary for an empty collection/run.
    write_ingestion_summary(summary_path, summary)

    print(f"\n=======================================================")
    print(f"✨ Done! {len(file_stats)} new documents | {total_chunks_added} chunks added")
    print(f"📂 Summary → {summary_path}")

if __name__ == "__main__":
    main()
