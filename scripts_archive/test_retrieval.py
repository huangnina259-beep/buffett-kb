
import sys
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Add src to path
sys.path.insert(0, str(Path("buffett_kb/src")))

DB_DIR = Path("buffett_kb/database")
COLLECTION_NAME = "buffett_kb"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def test_retrieval():
    print(f"Connecting to database at {DB_DIR}...")
    try:
        ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        client = chromadb.PersistentClient(path=str(DB_DIR))
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
        
        question = "What is the margin of safety?"
        print(f"Searching for: '{question}'")
        
        results = collection.query(
            query_texts=[question],
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )
        
        print(f"\nFound {len(results['documents'][0])} results:")
        for i, (doc, meta, dist) in enumerate(zip(results["documents"][0], results["metadatas"][0], results["distances"][0]), 1):
            relevance = 1.0 - dist
            print(f"\n[{i}] Source: {meta.get('source_label', 'N/A')} (Relevance: {relevance:.4f})")
            print(f"Content: {doc[:200]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_retrieval()
