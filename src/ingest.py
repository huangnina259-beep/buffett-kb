"""
Ingest all Buffett documents into ChromaDB.
This version handles large PDFs by processing page-by-page to avoid MemoryError.
"""

import argparse
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pdfplumber
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ── paths ─────────────────────────────────────────────────────────────────────
SRC_DIR  = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR   = ROOT_DIR / "database"
DATA_DIR = ROOT_DIR / "data" / "pdfs"

# ── constants ─────────────────────────────────────────────────────────────────
COLLECTION_NAME = "buffett_kb"
EMBED_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE      = 2000   # chars ≈ 500-600 tokens
CHUNK_OVERLAP   = 400    # chars ≈ 100 tokens

# ── text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple character-based chunker that prefers paragraph breaks."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # prefer paragraph break
            pb = text.rfind("\n\n", start + size // 2, end)
            if pb != -1:
                end = pb
            else:
                # fall back to sentence break
                sb = text.rfind(". ", start + size // 2, end)
                if sb != -1:
                    end = sb + 1
        chunk = text[start:end].strip()
        if len(chunk) > 80:
            chunks.append(chunk)
        start = end - overlap

    return chunks

def get_file_metadata(file_path: Path):
    """Try to guess metadata from filename."""
    name = file_path.name
    year = 0
    year_match = re.search(r"(19|20)\d{2}", name)
    if year_match:
        year = int(year_match.group(0))
    
    label = name.replace(".pdf", "").replace("_", " ")
    doc_type = "document"
    
    if "meeting" in name.lower() or "session" in name.lower():
        doc_type = "meeting_transcript"
    elif "letter" in name.lower():
        doc_type = "shareholder_letter"
    elif "valuation" in name.lower():
        doc_type = "valuation_guide"
        
    return {
        "source_label": label,
        "year": year,
        "doc_type": doc_type,
        "source_file": name
    }

# ── Main Ingestion ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Reprocess all files")
    args = parser.parse_args()

    print("🚀 Initialising ChromaDB...")
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

    # Check already processed files
    processed_files = set()
    summary_path = DB_DIR / "ingestion_summary.json"
    if summary_path.exists() and not args.force:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
            processed_files = set(summary.get("files", {}).keys())

    if not DATA_DIR.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        return

    all_pdfs = list(DATA_DIR.glob("*.pdf"))
    print(f"Found {len(all_pdfs)} PDFs in {DATA_DIR}")

    total_chunks_added = 0
    file_stats = {}

    for pdf_path in all_pdfs:
        if pdf_path.name in processed_files:
            print(f"⏭️ Skipping {pdf_path.name} (already processed)")
            continue

        print(f"📄 Processing {pdf_path.name} page-by-page...")
        metadata = get_file_metadata(pdf_path)
        file_chunks_count = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    chunks = chunk_text(text)
                    if not chunks:
                        continue
                    
                    ids = [f"{pdf_path.name}_p{i}_{j}" for j in range(len(chunks))]
                    metas = []
                    for j in range(len(chunks)):
                        m = metadata.copy()
                        m["page"] = i + 1
                        m["chunk_index"] = file_chunks_count + j
                        metas.append(m)

                    collection.add(
                        ids=ids,
                        documents=chunks,
                        metadatas=metas
                    )
                    file_chunks_count += len(chunks)
                    
                    if (i + 1) % 50 == 0:
                        print(f"  ... processed {i+1}/{total_pages} pages")

            print(f"✅ Ingested {file_chunks_count} chunks from {pdf_path.name}")
            total_chunks_added += file_chunks_count
            file_stats[pdf_path.name] = {
                "chunks": file_chunks_count,
                "ingested_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")

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
