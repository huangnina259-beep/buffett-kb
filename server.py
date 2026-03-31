import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # Load ANTHROPIC_API_KEY from .env if present

# Add src to path so we can import rag
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))
from rag import query_knowledge_base

app = FastAPI()

frontend_dir = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

class ChatRequest(BaseModel):
    query: str
    history: list = []

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(frontend_dir / "index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
async def chat(request: ChatRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY environment variable is missing."}, status_code=500)
        
    result = query_knowledge_base(request.query, history=request.history, api_key=api_key)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
