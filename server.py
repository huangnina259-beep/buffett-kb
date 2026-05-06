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

class QueryRequest(BaseModel):
    question: str
    language: str = "cn"
    history: list = []

class GymFeedbackRequest(BaseModel):
    case_id: str
    round: int
    question: str
    answer: str
    language: str = "cn"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(frontend_dir / "index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/qa", response_class=HTMLResponse)
@app.get("/qa.html", response_class=HTMLResponse)
async def qa_page():
    with open(frontend_dir / "qa.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/gym", response_class=HTMLResponse)
@app.get("/gym.html", response_class=HTMLResponse)
async def gym_page():
    with open(frontend_dir / "gym.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/tutor", response_class=HTMLResponse)
async def tutor_page():
    with open(react_dist / "index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/query")
async def query(request: QueryRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY not set"}, status_code=500)

    from rag import query_knowledge_base
    result = query_knowledge_base(request.question, history=request.history, api_key=api_key)

    error = result.get("error")
    answer = result.get("answer", "")
    if not answer and error:
        answer = f"[系统错误] {error}"

    sources = [
        {"title": s.get("label", ""), "author": s.get("author", ""), "text": s.get("text", "")}
        for s in result.get("sources", [])
    ]
    return {"answer": answer, "sources": sources, "follow_ups": result.get("follow_ups", [])}


GYM_SYSTEM_CN = """你是复利国的价值投资导师。你的风格是严谨、真诚、有洞察力——像芒格一样直接，像巴菲特一样温和。

你的任务：评估学员对价值投资案例问题的回答，给出有深度的反馈。

反馈要求：
- 150-200字，聚焦最重要的1-2个概念
- 指出学员答对的部分（鼓励正确思维）
- 指出遗漏或需要深化的部分
- 用巴菲特/芒格/Graham的视角来补充
- 不要给分数，不要说"很好"这种空洞评价
- key_concepts 列出3-5个本轮核心概念（中文词语）

必须返回严格的JSON格式（不要markdown，不要代码块）：
{"feedback": "...", "key_concepts": ["概念1", "概念2", "概念3"]}"""

GYM_SYSTEM_EN = """You are a value investing mentor at The Compounder. Your style is rigorous and insightful — direct like Munger, warm like Buffett.

Your task: Evaluate a student's answer to a value investing case study question and provide substantive feedback.

Feedback requirements:
- 150-200 words, focused on 1-2 key ideas
- Acknowledge what the student got right (reinforce correct thinking)
- Point out what was missing or needs deepening
- Add perspective from Buffett/Munger/Graham's viewpoint
- No scores, no hollow praise like "great job"
- key_concepts: list 3-5 core concepts from this round (short English phrases)

Must return strict JSON (no markdown, no code blocks):
{"feedback": "...", "key_concepts": ["concept 1", "concept 2", "concept 3"]}"""

GYM_ROUND_CONTEXT = {
    "cocacola": {
        "cn": [
            "第一轮：理解商业模式。重点概念：浓缩液模式、轻资产、装瓶商网络、高毛利率",
            "第二轮：经济护城河。重点概念：品牌溢价、情感护城河、分销网络、定价权、持久性",
            "第三轮：管理层评估。重点概念：资本分配、戈伊苏埃塔改革、股份回购、ROE提升",
            "第四轮：财务健康分析。重点概念：高ROE、自由现金流、净利润率、轻资产回报率",
            "第五轮：估值与安全边际。重点概念：内在价值、DCF思维、安全边际、长期复利",
        ],
        "en": [
            "Round 1: Understanding the business model. Key concepts: concentrate model, asset-light, bottler network, high margins",
            "Round 2: Economic moat. Key concepts: brand premium, emotional moat, distribution network, pricing power, durability",
            "Round 3: Management quality. Key concepts: capital allocation, Goizueta's reforms, share buybacks, ROE improvement",
            "Round 4: Financial analysis. Key concepts: high ROE, free cash flow, net margin, asset-light returns",
            "Round 5: Valuation & margin of safety. Key concepts: intrinsic value, DCF thinking, margin of safety, long-term compounding",
        ]
    }
}


@app.post("/gym/feedback")
async def gym_feedback(request: GymFeedbackRequest):
    import json as json_lib
    from anthropic import Anthropic

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY not set"}, status_code=500)

    lang = request.language
    system = GYM_SYSTEM_CN if lang == "cn" else GYM_SYSTEM_EN

    case_ctx = GYM_ROUND_CONTEXT.get(request.case_id, {}).get(lang, [])
    context = case_ctx[request.round] if request.round < len(case_ctx) else ""

    if lang == "cn":
        user_msg = f"{context}\n\n问题：{request.question}\n学员回答：{request.answer}"
    else:
        user_msg = f"{context}\n\nQuestion: {request.question}\nStudent answer: {request.answer}"

    client_ant = Anthropic(api_key=anthropic_key)
    response = client_ant.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    try:
        return json_lib.loads(text)
    except json_lib.JSONDecodeError:
        return {"feedback": text, "key_concepts": []}


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
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY environment variable is missing."}, status_code=500)

    from rag import query_knowledge_base
    result = query_knowledge_base(request.query, history=request.history, api_key=api_key)
    return result

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    logging.info(f"[RAG] Request received: {request.query[:80]!r}")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        import json
        error_event = f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY environment variable is missing.'})}\n\n"
        return StreamingResponse(iter([error_event]), media_type="text/event-stream")

    from rag import stream_query_knowledge_base

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
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        import json
        error_event = f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY environment variable is missing.'})}\n\n"
        return StreamingResponse(iter([error_event]), media_type="text/event-stream")

    from tutor import stream_tutor_response

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
