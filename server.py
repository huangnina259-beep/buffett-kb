import logging
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

load_dotenv()  # Load MINIMAX_API_KEY from .env if present

# Add src to path so we can import rag
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))
from rag import query_knowledge_base, stream_query_knowledge_base
from tutor import stream_tutor_response

app = FastAPI()

# CORS — needed when React dev server (port 5173) talks to FastAPI (port 8000)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "https://huangnina259-beep.github.io",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).parent / "frontend"
react_dist   = Path(__file__).parent / "react-app" / "dist"

# Old Q&A frontend assets at /static
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
# React tutor assets at /assets (matches Vite build output paths)
if react_dist.exists() and (react_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(react_dist / "assets")), name="react-assets")

class DigestRequest(BaseModel):
    prompt: str
    system: str

class ChatRequest(BaseModel):
    query: str
    history: list = []

class TutorRequest(BaseModel):
    message: str
    history: list = []
    curriculum_state: dict = {}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(frontend_dir / "index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/tutor", response_class=HTMLResponse)
async def tutor_page():
    """Serve the React tutor training app."""
    with open(react_dist / "index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/digest")
async def digest(request: DigestRequest):
    """LLM call for daily business briefing — no RAG, just generation."""
    import os
    from openai import OpenAI

    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"error": "MINIMAX_API_KEY not set"}, status_code=500)

    llm_model    = os.environ.get("LLM_MODEL", "MiniMax-Text-01")
    llm_base_url = os.environ.get("LLM_BASE_URL", "https://api.minimax.io/v1")

    try:
        client = OpenAI(api_key=api_key, base_url=llm_base_url)
        response = client.chat.completions.create(
            model=llm_model,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user",   "content": request.prompt},
            ],
        )
        return {"content": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"error": "MINIMAX_API_KEY environment variable is missing."}, status_code=500)

    result = query_knowledge_base(request.query, history=request.history, api_key=api_key)
    return result

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    logging.info(f"[RAG] Request received: {request.query[:80]!r}")
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        import json
        error_event = f"data: {json.dumps({'type': 'error', 'message': 'MINIMAX_API_KEY environment variable is missing.'})}\n\n"
        return StreamingResponse(iter([error_event]), media_type="text/event-stream")

    def generate():
        yield from stream_query_knowledge_base(request.query, history=request.history, api_key=api_key)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/tutor/stream")
async def tutor_stream(request: TutorRequest):
    logging.info(f"[Tutor] Request received: {request.message[:80]!r}")
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        import json
        error_event = f"data: {json.dumps({'type': 'error', 'message': 'MINIMAX_API_KEY environment variable is missing.'})}\n\n"
        return StreamingResponse(iter([error_event]), media_type="text/event-stream")

    def generate():
        yield from stream_tutor_response(
            request.message,
            history=request.history,
            curriculum_state=request.curriculum_state,
            api_key=api_key,
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
