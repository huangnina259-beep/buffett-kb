import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path("buffett_kb/src")))
import google.generativeai as genai
from rag import _get_collection, GEMINI_MODEL

api_key = os.environ.get("GOOGLE_API_KEY", "")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY is not configured")
genai.configure(api_key=api_key)

def test():
    q = "2008年金融危机时，巴菲特在股东信里传达了什么情绪？"
    
    # 1. Translate
    trans_model = genai.GenerativeModel(model_name=GEMINI_MODEL)
    prompt = f"Translate the following user question into English. Only return the English translation:\n\n{q}"
    trans_res = trans_model.generate_content(prompt)
    search_query = trans_res.text.strip()
    print(f"Translated query: {search_query}")
    
    # 2. Retrieve
    collection = _get_collection()
    results = collection.query(
        query_texts=[search_query],
        n_results=10,
        include=["documents", "metadatas", "distances"]
    )
    
    print("\n--- Retrieved Documents ---")
    for i, (doc, meta, dist) in enumerate(zip(results["documents"][0], results["metadatas"][0], results["distances"][0])):
        relevance = 1.0 - dist
        print(f"[{i+1}] {meta['source_label']} (Year: {meta.get('year', '')}) - Rel: {relevance:.4f}")
        print(f"Snippet: {doc[:150]}...\n")

if __name__ == "__main__":
    test()
