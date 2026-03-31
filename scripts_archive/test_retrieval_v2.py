import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path("buffett_kb/src")))
import google.generativeai as genai
from rag import query_knowledge_base

os.environ["GOOGLE_API_KEY"] = "AIzaSyAnsO2yoVd-b3C9KQ67OCCi99RpsHjXlJA"

def test():
    q = "2008年金融危机时，巴菲特在股东信里传达了什么情绪？"
    print(f"Query: {q}\n")
    
    result = query_knowledge_base(q, top_k=5)
    
    print("--- Answer ---")
    print(result.get("answer"))
    
    print("\n--- Sources ---")
    for i, s in enumerate(result.get("sources", [])):
        print(f"[{i+1}] {s['label']} (Year: {s.get('year', '')}, Type: {s.get('doc_type', '')}) - Rel: {s['relevance']:.4f}")

if __name__ == "__main__":
    test()
