"""
Ingest all Buffett documents into ChromaDB from the Cleaned Markdown Knowledge Base.
Parses YAML frontmatter for precise metadata.
Uses Langchain's RecursiveCharacterTextSplitter to avoid MemoryErrors.
"""

import argparse
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── paths ─────────────────────────────────────────────────────────────────────
SRC_DIR  = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR   = ROOT_DIR / "database"
MD_DIR   = ROOT_DIR / "data" / "clean_mds"

# ── constants ─────────────────────────────────────────────────────────────────
COLLECTION_NAME = "buffett_kb"
EMBED_MODEL     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE      = 2000   # chars ≈ 500-600 tokens
CHUNK_OVERLAP   = 400    # chars ≈ 100 tokens

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    is_separator_regex=False,
)

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
    language = "en"  # Default to English
    if "_CN.md" in name or any('\u4e00' <= char <= '\u9fff' for char in name):
        language = "zh"
    elif "_EN.md" in name:
        language = "en"
            
    return {
        "source_label": label,
        "year": year,
        "doc_type": doc_type,
        "source_file": name,
        "language": language
    }, content

# ── Main Ingestion ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Reprocess all files")
    args = parser.parse_args()

    print("🚀 Initialising ChromaDB...")
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

    processed_files = set()
    summary_path = DB_DIR / "ingestion_summary.json"
    if summary_path.exists() and not args.force:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
            processed_files = set(summary.get("files", {}).keys())

    if not MD_DIR.exists():
        print(f"❌ Clean Markdown directory not found: {MD_DIR}")
        return

    all_mds = list(MD_DIR.glob("*.md"))
    print(f"Found {len(all_mds)} Markdown files in {MD_DIR}")

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
        
        batch_size = 100
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
                collection.add(
                    ids=ids,
                    documents=batch_chunks,
                    metadatas=metas
                )
            except Exception as e:
                print(f"❌ Error adding batch to ChromaDB for {md_path.name}: {e}")

        print(f"✅ Ingested {len(chunks)} chunks from {md_path.name}")
        total_chunks_added += len(chunks)
        file_stats[md_path.name] = {
            "chunks": len(chunks),
            "ingested_at": datetime.now().isoformat()
        }

    # Update summary
    new_summary = {"files": file_stats, "total_chunks": total_chunks_added}
    if summary_path.exists() and not args.force:
        with open(summary_path, "r", encoding="utf-8") as f:
            old_summary = json.load(f)
            old_summary["files"].update(file_stats)
            old_summary["total_chunks"] = old_summary.get("total_chunks", 0) + total_chunks_added
            new_summary = old_summary

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(new_summary, f, indent=2, ensure_ascii=False)

    print(f"\n=======================================================")
    print(f"✨ Done! {len(file_stats)} new documents | {total_chunks_added} chunks added")
    print(f"📂 Summary → {summary_path}")

if __name__ == "__main__":
    main()
