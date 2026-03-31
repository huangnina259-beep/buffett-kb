import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add src to path so we can import rag
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))
from rag import query_knowledge_base

def test():
    print("Testing 'What is a moat?'...")
    result = query_knowledge_base("What is a moat?")
    print("Answer snippet:")
    print(result.get("answer", "")[:500])
    print("\nFollow ups:")
    print(result.get("follow_ups", []))

if __name__ == "__main__":
    test()
