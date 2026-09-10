import logging
import json
import os
import secrets
import sys
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

load_dotenv(Path(__file__).parent / ".env", override=True)  # Load API keys from .env if present

# Add src to path so we can import rag
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))
from coach import stream_coach_response
from ai_gateway import get_generation_gateway, parse_json_text
from embedding_gateway import get_embedding_gateway
from vector_store import index_status
from ai_settings import (
    find_profile,
    load_effective_settings,
    load_saved_settings,
    public_settings,
    save_settings,
)
from reranker_gateway import (
    RerankerGateway,
    RerankerProfile,
    get_reranker_gateway,
    reset_reranker_gateway,
)
from starlette.concurrency import run_in_threadpool

app = FastAPI()


@app.middleware("http")
async def protect_deployed_model_settings(request, call_next):
    # Public deployments are configured through Railway, not anonymous visitors.
    protected = request.url.path == "/api/ai/test" or (
        request.url.path == "/api/ai/settings" and request.method != "GET"
    )
    if protected and os.environ.get("RAILWAY_ENVIRONMENT_ID"):
        token = os.environ.get("API_ADMIN_TOKEN", "")
        supplied = request.headers.get("Authorization", "")
        if not token or not secrets.compare_digest(supplied, f"Bearer {token}"):
            return JSONResponse(status_code=403, content={
                "message": "线上模型设置仅允许管理员修改。"
            })
    return await call_next(request)

@app.middleware("http")
async def identify_coach_visitor(request, call_next):
    if request.url.path != "/coach" and not request.url.path.startswith("/api/coach/"):
        return await call_next(request)
    visitor = request.cookies.get("fuliguo_visitor", "")
    try:
        visitor = str(_uuid.UUID(visitor))
    except (ValueError, AttributeError):
        visitor = str(_uuid.uuid4())
    request.state.visitor_id = visitor
    response = await call_next(request)
    response.set_cookie("fuliguo_visitor", visitor, max_age=31536000,
                        httponly=True, samesite="lax",
                        secure=bool(os.environ.get("RAILWAY_ENVIRONMENT_ID")))
    return response


def coach_visitor(request: Request):
    return request.state.visitor_id


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
CASE_LIBRARY = json.loads((frontend_dir / "cases.json").read_text(encoding="utf-8"))

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

class GymSynthesisRequest(BaseModel):
    case_id: str
    answers: list[str]
    feedbacks: list[str]
    language: str = "cn"

class AnalystFeedbackRequest(BaseModel):
    company: str           # user-supplied company name (e.g. "苹果", "茅台", "Microsoft")
    framework: str         # one of: business_model | moat | management | margin_of_safety
    question: str          # the question text the user was answering
    answer: str            # the user's answer
    language: str = "cn"

class AnalystSynthesisRequest(BaseModel):
    company: str
    answers: list[str]     # 4 answers, one per framework
    feedbacks: list[str]   # 4 feedback summaries
    language: str = "cn"


class AISettingsRequest(BaseModel):
    providers: list[dict]
    routes: dict[str, str]
    vector_collection: str = "buffett_kb"


class AIConnectionTestRequest(BaseModel):
    provider_id: str
    provider: str = "openai_compatible"
    base_url: str = ""
    model: str
    capability: str
    api_key: str = ""


class FeedbackResponse(BaseModel):
    feedback: str
    key_concepts: list[str]


def _validated_feedback(text: str):
    try:
        value = FeedbackResponse.model_validate(parse_json_text(text))
        return value.model_dump()
    except (ValueError, TypeError, ValidationError) as exc:
        logging.warning("[AI] Invalid structured feedback response: %s", exc)
        return JSONResponse(
            content={
                "error": "MODEL_OUTPUT_INVALID",
                "message": "模型未返回有效的反馈结构，请重试或更换模型。",
            },
            status_code=502,
        )

@app.get("/health")
async def health():
    embedding = get_embedding_gateway().status()
    vector_index = index_status()
    knowledge_status = "ready"
    if vector_index.get("status") == "unavailable":
        knowledge_status = "index_unavailable"
    elif not vector_index.get("count"):
        knowledge_status = "index_empty"
    elif not embedding.get("configured"):
        knowledge_status = "embedding_not_configured"
    else:
        try:
            from vector_store import ensure_index_compatible
            ensure_index_compatible()
        except Exception:
            knowledge_status = "index_incompatible"
    return {
        "status": "ok",
        "knowledge_status": knowledge_status,
        "generation": get_generation_gateway().status(),
        "embedding": embedding,
        "reranker": get_reranker_gateway().status(),
        "vector_index": vector_index,
    }


@app.get("/api/ai/settings")
async def get_ai_settings():
    """Return editable settings without ever exposing stored API keys."""
    return public_settings()


@app.put("/api/ai/settings")
async def put_ai_settings(request: AISettingsRequest):
    previous = load_saved_settings()
    previous_embedding = (previous or {}).get("routes", {}).get("embedding")
    previous_collection = (previous or {}).get("vector_collection")
    try:
        saved = save_settings(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Settings are cached for request performance; invalidate all affected gateways.
    from ai_gateway import reset_generation_gateway
    from embedding_gateway import reset_embedding_gateway

    reset_generation_gateway()
    reset_embedding_gateway()
    reset_reranker_gateway()
    new_embedding = saved.get("routes", {}).get("embedding")
    return {
        "settings": public_settings(saved),
        "reindex_required": bool(
            previous_embedding != new_embedding
            or previous_collection != saved.get("vector_collection")
        ),
        "message": "模型配置已保存。",
    }


def _resolve_test_key(request: AIConnectionTestRequest) -> str:
    if request.api_key.strip():
        return request.api_key.strip()
    saved = load_saved_settings()
    if saved:
        for provider in saved.get("providers", []):
            if provider.get("id") == request.provider_id:
                return str(provider.get("api_key") or "")
    return ""


def _run_ai_connection_test(request: AIConnectionTestRequest) -> dict:
    from ai_gateway import AnthropicAdapter, ModelProfile, OpenAICompatibleAdapter
    from embedding_gateway import EmbeddingProfile, OpenAIEmbeddingAdapter

    key = _resolve_test_key(request)
    if not key:
        raise ValueError("请先输入 API Key，或保存一个已配置的 Key。")
    started = time.perf_counter()
    provider_type = request.provider.strip().lower()
    base_url = request.base_url.strip().rstrip("/")
    capability = request.capability.strip().lower()

    if capability == "generation":
        profile = ModelProfile(
            name="connection_test",
            provider=provider_type,
            model=request.model.strip(),
            api_key_value=key,
            base_url=base_url or None,
        )
        adapter = AnthropicAdapter() if provider_type == "anthropic" else OpenAICompatibleAdapter()
        result = adapter.complete(
            profile,
            system="You are a connection test.",
            messages=[{"role": "user", "content": "Reply with OK only."}],
            max_tokens=128,
            temperature=0,
            json_mode=False,
        )
        detail = result.text.strip()[:100] or "模型已响应"
        extra = {}
    elif capability == "embedding":
        if provider_type == "anthropic":
            raise ValueError("Anthropic 供应商不支持 OpenAI 兼容向量接口。")
        profile = EmbeddingProfile(
            name="connection_test",
            provider="openai" if provider_type == "openai" else "openai_compatible",
            model=request.model.strip(),
            api_key_value=key,
            base_url=base_url or None,
        )
        vector = OpenAIEmbeddingAdapter().embed_query(profile, "connection test")
        detail = "向量接口返回正常"
        extra = {"dimension": len(vector)}
    elif capability == "reranker":
        profile = RerankerProfile(
            name="connection_test",
            provider=provider_type,
            model=request.model.strip(),
            base_url=base_url,
            api_key=key,
        )
        ranked = RerankerGateway(profile).rerank(
            "value investing",
            ["A document about cooking.", "A document about durable business value."],
            top_n=2,
        )
        detail = f"重排接口返回 {len(ranked)} 条结果"
        extra = {"results": len(ranked)}
    else:
        raise ValueError("未知模型能力类型。")

    return {
        "ok": True,
        "detail": detail,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        **extra,
    }


@app.post("/api/ai/test")
async def test_ai_connection(request: AIConnectionTestRequest):
    try:
        return await run_in_threadpool(_run_ai_connection_test, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.warning(
            "[AI settings] connection test failed provider=%s model=%s: %s",
            request.provider_id,
            request.model,
            exc,
        )
        status = getattr(exc, "status_code", None)
        message = "连接测试失败，请检查 API 地址、Key 和模型名称。"
        if status:
            message += f"（HTTP {status}）"
        raise HTTPException(status_code=502, detail=message) from exc

@app.get("/app", response_class=HTMLResponse)
@app.get("/app/{rest:path}", response_class=HTMLResponse)
async def react_app(rest: str = ""):
    index = react_dist / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>React app not built</h1>", status_code=503)
    with open(index, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
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
        data = json.dumps(CASE_LIBRARY, ensure_ascii=False).replace("<", "\\u003c")
        return f.read().replace("__CASE_LIBRARY__", data)

@app.get("/tutor", response_class=HTMLResponse)
@app.get("/tutor.html", response_class=HTMLResponse)
async def tutor_page():
    with open(frontend_dir / "tutor.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/analyst", response_class=HTMLResponse)
@app.get("/analyst.html", response_class=HTMLResponse)
async def analyst_page():
    with open(frontend_dir / "analyst.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/query")
async def query(request: QueryRequest):
    from rag import query_knowledge_base
    result = query_knowledge_base(request.question, history=request.history)

    error = result.get("error")
    answer = result.get("answer", "")
    if not answer and error:
        return JSONResponse(status_code=503, content={
            "error": result.get("error_code", "KNOWLEDGE_UNAVAILABLE"),
            "message": "知识库暂时不可用，请稍后重试。",
            "answer": "知识库暂时不可用，请稍后重试。",
            "sources": [], "follow_ups": [],
        })

    sources = [
        {**s, "title": s.get("label", "")}
        for s in result.get("sources", [])
    ]
    return {"answer": answer, "sources": sources, "follow_ups": result.get("follow_ups", [])}


GYM_SYSTEM_CN = """你是复利国的价值投资导师。风格：像芒格一样直接，像巴菲特一样温和。

你的任务：基于提供的知识库原文，评估学员的案例分析回答。

反馈要求：
- 200-280字，聚焦最重要的1-2个概念
- 若学员答对了，具体指出为什么对；若没有答对，坦诚指出关键误区，不要空洞夸奖
- 再指出遗漏或需要深化的地方
- **必须引用知识库原文**支撑你的每一个核心观点，格式：「原文」——作者/来源
- 如果知识库里没有直接相关原文，直接说"知识库里没有关于这点的直接记录"
- 不给分数，不把历史案例写成当下买卖建议；只能评价学员实际写出的内容，跳过不代表掌握
- key_concepts 列出3-5个本轮核心概念（中文词语）

返回严格JSON（不要代码块）：
{"feedback": "反馈正文（可用**加粗**强调关键词）", "key_concepts": ["概念1", "概念2"]}"""

GYM_SYSTEM_EN = """You are a value investing mentor at The Compounder. Direct like Munger, warm like Buffett.

Your task: Evaluate the student's case analysis using the knowledge base excerpts provided.

Feedback requirements:
- 200-280 words, focused on 1-2 key concepts
- First: acknowledge what the student got right (be specific, no hollow praise)
- Then: point out what's missing or needs deepening
- **Must quote the knowledge base** to support every core point. Format: "quote" — Author/Source
- If there's no directly relevant excerpt, say "The knowledge base has no direct record on this point"
- No scores
- key_concepts: 3-5 core concepts for this round (short phrases)

Return strict JSON (no code blocks):
{"feedback": "feedback text (can use **bold** for key terms)", "key_concepts": ["concept 1", "concept 2"]}"""

# The page and feedback engine share one reviewed case catalog.
GYM_ROUND_QUERIES = {key: [r["retrieval_query"] for r in case["rounds"]]
                     for key, case in CASE_LIBRARY.items()}
GYM_ROUND_CONTEXT = {key: {lang: [r[lang]["name"] + "：" + r[lang]["hint"]
                                 for r in case["rounds"]] for lang in ("cn", "en")}
                     for key, case in CASE_LIBRARY.items()}


def require_case(case_id, round_index=None):
    case = CASE_LIBRARY.get(case_id)
    if case is None or (round_index is not None and not 0 <= round_index < len(case["rounds"])):
        raise HTTPException(status_code=422, detail="案例或训练轮次无效")
    return case


@app.post("/gym/feedback")
async def gym_feedback(request: GymFeedbackRequest):
    case = require_case(request.case_id, request.round)
    lang = request.language

    # Retrieve knowledge base context for this round
    kb_context = ""
    try:
        from rag import retrieve_context
        queries = GYM_ROUND_QUERIES.get(request.case_id, [])
        query = queries[request.round] if request.round < len(queries) else request.question
        kb_context, _ = retrieve_context(query, top_k=8)
    except Exception as e:
        logging.warning(f"[Gym] KB retrieval failed: {e}")

    if not kb_context.strip():
        return JSONResponse(status_code=503, content={
            "error": "KNOWLEDGE_CONTEXT_UNAVAILABLE",
            "message": "暂时无法取得本案例的参考资料，请稍后重试。",
        })

    round_ctx = (GYM_ROUND_CONTEXT.get(request.case_id, {}).get(lang, []) or [])[request.round] \
        if request.round < len(GYM_ROUND_CONTEXT.get(request.case_id, {}).get(lang, [])) else ""

    if lang == "cn":
        user_msg = (
            f"【知识库原文摘录】\n{kb_context}\n\n"
            f"---\n\n"
            f"【本轮主题】{round_ctx}\n\n"
            f"【学员问题】{request.question}\n"
            f"【学员回答】{request.answer}\n\n"
            f"请基于以上知识库内容给出反馈，必须引用原文。"
        )
    else:
        user_msg = (
            f"[Knowledge base excerpts]\n{kb_context}\n\n"
            f"---\n\n"
            f"[Round context] {round_ctx}\n\n"
            f"[Question] {request.question}\n"
            f"[Student answer] {request.answer}\n\n"
            f"Give feedback based on the knowledge base above. Must quote original text."
        )

    response = get_generation_gateway().complete(
        "structured_feedback",
        max_tokens=4096,
        system=GYM_SYSTEM_CN if lang == "cn" else GYM_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
    )

    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return _validated_feedback(text)


SYNTHESIS_SYSTEM_CN = """你是复利国的价值投资导师。学员刚完成了一个完整的五轮案例分析训练。

你的任务：基于知识库原文和学员的全部回答+反馈，写一份有深度的综合投资分析。

格式要求：
## 本案例的核心判断
用2-3句话解释这份历史案例的商业机制与局限，必须引用知识库原文支撑。不要将历史案例写成当前买入或持有建议。

## 学员思维优势
具体指出学员在哪1-2个维度上展现了正确的价值投资思维，引用其原话印证。

## 需要强化的思维模式
指出1-2个最重要的认知盲点，不是批评，而是指向下一步成长的方向，配合知识库原文说明为什么这个方向重要。

## 大师的最终洞见
从知识库里找出1-2条巴菲特/芒格/Marks/李录对这家公司或相关原则最深刻的原话，做最后的升华。格式：「原文」——作者

规则：
- 全文400-600字
- 每个核心观点必须有知识库原文引用，格式：「原文」——作者
- 不要给分数，不要说"表现优秀"这种空话
- 直接用markdown，不要代码块"""

SYNTHESIS_SYSTEM_EN = """You are a value investing mentor at The Compounder. The student just completed a full five-round case analysis.

Your task: Write a substantive synthesis based on the knowledge base and the student's complete answers and feedback.

Format:
## Core lesson
Explain the historical business mechanism and its limitations in 2-3 sentences. Cite the evidence. Do not turn a historical case into a current investment recommendation.

## Student's Strengths
Identify 1-2 dimensions where the student showed correct value investing thinking. Quote their own words to confirm.

## Thinking Patterns to Strengthen
Identify 1-2 key blind spots — not criticism, but direction for growth. Use KB quotes to explain why this matters.

## The Master's Final Insight
Find 1-2 of the deepest quotes from Buffett/Munger/Marks/Li Lu about this company or related principles. Format: "quote" — Author

Rules:
- 400-600 words total
- Every core point needs a KB citation: "quote" — Author
- No scores, no hollow praise
- Direct markdown, no code blocks"""


@app.post("/gym/synthesis")
async def gym_synthesis(request: GymSynthesisRequest):
    case = require_case(request.case_id)
    lang = request.language

    # Broad KB retrieval covering the full case
    kb_context = ""
    try:
        from rag import retrieve_context
        query = case["synthesis_query"]
        kb_context, _ = retrieve_context(query, top_k=10)
    except Exception as e:
        logging.warning(f"[Gym synthesis] KB retrieval failed: {e}")

    if not kb_context.strip():
        return JSONResponse(status_code=503, content={
            "error": "KNOWLEDGE_CONTEXT_UNAVAILABLE",
            "message": "暂时无法取得本案例的参考资料，请稍后重试。",
        })

    round_names = [r["cn" if lang == "cn" else "en"]["name"] for r in case["rounds"]]

    answers_block = "\n\n".join(
        f"【{round_names[i]}】\n{request.answers[i] or ('（已跳过）' if lang == 'cn' else '(Skipped)')}"
        for i in range(min(len(request.answers), len(round_names)))
    )
    feedbacks_block = "\n\n".join(
        f"【{round_names[i]} 反馈摘要】\n{request.feedbacks[i][:200] if i < len(request.feedbacks) else ''}"
        for i in range(min(len(request.answers), len(round_names)))
    )

    if lang == "cn":
        user_msg = (
            f"【知识库原文摘录】\n{kb_context}\n\n"
            f"---\n\n【学员的五轮回答】\n{answers_block}\n\n"
            f"---\n\n【各轮反馈摘要】\n{feedbacks_block}\n\n"
            f"请写综合投资分析。"
        )
    else:
        user_msg = (
            f"[Knowledge base excerpts]\n{kb_context}\n\n"
            f"---\n\n[Student's five answers]\n{answers_block}\n\n"
            f"---\n\n[Round feedback summaries]\n{feedbacks_block}\n\n"
            f"Write the synthesis."
        )

    response = get_generation_gateway().complete(
        "long_synthesis",
        max_tokens=4096,
        system=SYNTHESIS_SYSTEM_CN if lang == "cn" else SYNTHESIS_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
    )

    return {"synthesis": response.text.strip()}


# ── Analyst tool: user-selected company, 4-framework guided analysis ────────

ANALYST_FEEDBACK_SYSTEM_CN = """你是复利国的价值投资助手。学员正在用 4 框架(商业模式/护城河/管理层/安全边际)分析一家**他自己选的公司**。

你的任务:基于知识库原文 + 你对价值投资原则的理解,评估学员当前这一题的回答。

反馈要求:
- 200-280 字,聚焦本框架最关键的 1-2 个判断
- 先肯定答对的部分,具体指出**为什么对**(不空洞夸奖)
- 再指出遗漏或盲点,**用反问引导学员自己想**(不直接给答案)
- **只要 KB 里有相关原文,必须引用,格式:「原文」——作者**
- KB 没有这家公司的直接记录?**用同类公司或同类原则的 KB 原文做类比锚定**(比如分析新能源车,可引用 Buffett 关于汽车工业的判断)
- 反馈结尾必须有一句:「这个维度套到任何公司都该问 ___」(把案例抽象成框架)
- 不给买卖建议,不给目标价

返回严格 JSON(不要代码块):
{"feedback": "反馈正文(可用 **加粗** 强调)", "key_concepts": ["概念1", "概念2", "概念3"]}"""

ANALYST_FEEDBACK_SYSTEM_EN = """You are a value investing assistant at The Compounder. The student is analyzing a company they chose themselves, using the 4-framework method (Business Model / Moat / Management / Margin of Safety).

Your task: evaluate their answer for the current framework, grounded in the knowledge base.

Requirements:
- 200-280 words, focused on the 1-2 most important judgments for this framework
- First acknowledge what they got right (be specific, no hollow praise)
- Then surface gaps via Socratic questioning (don't just give the answer)
- **If the KB contains a relevant excerpt, you MUST quote it, format: "quote" — Author**
- KB has nothing on this exact company? Anchor by analogy using KB excerpts on similar companies or matching principles (e.g. analyzing an EV maker — quote Buffett on auto industry)
- End with: "Applied to any company, this dimension asks ___" (abstract case → framework)
- No buy/sell calls, no target prices

Return strict JSON (no code blocks):
{"feedback": "feedback text (can use **bold**)", "key_concepts": ["concept 1", "concept 2", "concept 3"]}"""

# Per-framework KB query templates — {company} substituted at runtime
ANALYST_FRAMEWORK_QUERIES = {
    "business_model":   "{company} business model how makes money revenue customers Buffett",
    "moat":             "{company} economic moat competitive advantage brand pricing power Buffett Munger",
    "management":       "{company} CEO management capital allocation buyback dividend acquisition Buffett",
    "margin_of_safety": "{company} valuation P/E ROIC free cash flow intrinsic value margin of safety Howard Marks",
}

ANALYST_FRAMEWORK_LABELS_CN = {
    "business_model":   "商业模式",
    "moat":             "护城河",
    "management":       "管理层",
    "margin_of_safety": "安全边际",
}

ANALYST_FRAMEWORK_LABELS_EN = {
    "business_model":   "Business Model",
    "moat":             "Moat",
    "management":       "Management",
    "margin_of_safety": "Margin of Safety",
}


@app.post("/analyst/feedback")
async def analyst_feedback(request: AnalystFeedbackRequest):

    lang = request.language
    framework = request.framework

    # Build KB query: company + framework template
    query_template = ANALYST_FRAMEWORK_QUERIES.get(framework, "{company} value investing analysis")
    kb_query = query_template.replace("{company}", request.company)

    kb_context = ""
    try:
        from rag import retrieve_context
        kb_context, _ = retrieve_context(kb_query, top_k=8)
    except Exception as e:
        logging.warning(f"[Analyst] KB retrieval failed: {e}")

    framework_label = (ANALYST_FRAMEWORK_LABELS_CN if lang == "cn" else ANALYST_FRAMEWORK_LABELS_EN).get(framework, framework)

    if lang == "cn":
        user_msg = (
            f"【知识库原文摘录】\n{kb_context}\n\n"
            f"---\n\n"
            f"【学员分析的公司】{request.company}\n"
            f"【本题框架】{framework_label}\n"
            f"【题目】{request.question}\n"
            f"【学员回答】{request.answer}\n\n"
            f"请基于知识库给反馈。如果 KB 里没有这家公司的直接记录,用同类公司/原则做类比锚定。"
        )
    else:
        user_msg = (
            f"[Knowledge base excerpts]\n{kb_context}\n\n"
            f"---\n\n"
            f"[Student's company] {request.company}\n"
            f"[Framework] {framework_label}\n"
            f"[Question] {request.question}\n"
            f"[Student answer] {request.answer}\n\n"
            f"Give feedback using the KB. If no direct record on this company, anchor by analogy."
        )

    response = get_generation_gateway().complete(
        "structured_feedback",
        max_tokens=4096,
        system=ANALYST_FEEDBACK_SYSTEM_CN if lang == "cn" else ANALYST_FEEDBACK_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return _validated_feedback(text)


ANALYST_SYNTHESIS_SYSTEM_CN = """你是复利国的价值投资助手。学员刚用 4 框架完整分析了一家公司,现在你要给一份"个人投资笔记"。

格式要求:

## 投资判断
2-3 句话:这家公司是不是值得 Buffett 式投资人关注的标的?**必须基于学员的回答 + KB 原文**得出结论,不要拍脑袋。

## 学员思维优势
具体指出学员在哪 1-2 个框架上展现了正确的价值投资思维。引用学员自己的话印证。

## 思维盲点
1-2 个最关键的认知盲点,不是批评,是下次分析任何公司时都该问的问题。配 KB 原文说明为什么这个角度重要。

## 大师对照
从知识库里找出 1-2 条 Buffett/Munger/Howard Marks/Li Lu 对这家公司或同类公司最深刻的原话。格式:「原文」——作者
**如果 KB 没有这家公司的直接记录**,引用一条最相关的同类原则。

## 你的下一步
1 句话:学员现在该再去年报里看哪个具体数字/章节,验证自己的判断?(如:看 10-K 里的 R&D 占比,或看股东信里 CEO 谈资本配置)

规则:
- 全文 400-600 字
- 每个核心观点必须 KB 引用
- 不给买卖建议,不给目标价
- 直接 markdown,无代码块"""

ANALYST_SYNTHESIS_SYSTEM_EN = """You are a value investing assistant at The Compounder. The student just completed a 4-framework analysis of a company they chose. Write their "personal investment memo".

Format:

## Investment Verdict
2-3 sentences: is this worth a Buffett-style investor's attention? Must be grounded in the student's answers + KB excerpts, not vibes.

## Student's Strengths
1-2 frameworks where they showed real value investing thinking. Quote their own words.

## Thinking Blind Spots
1-2 critical blind spots, framed as "questions to ask any company". Use KB to explain why each angle matters.

## Master's Mirror
1-2 deep quotes from Buffett/Munger/Howard Marks/Li Lu about this company or its peer category. Format: "quote" — Author. If KB has nothing on the exact company, quote the most relevant principle.

## Your Next Step
One sentence: which specific 10-K section / metric / shareholder letter should the student go read next to validate their thesis?

Rules:
- 400-600 words total
- Every core point needs a KB citation
- No buy/sell calls, no target prices
- Direct markdown, no code blocks"""


@app.post("/analyst/synthesis")
async def analyst_synthesis(request: AnalystSynthesisRequest):
    lang = request.language

    # Broad KB retrieval covering the company + general value investing principles
    kb_context = ""
    try:
        from rag import retrieve_context
        kb_query = f"{request.company} business model moat management valuation Buffett Munger value investing"
        kb_context, _ = retrieve_context(kb_query, top_k=10)
    except Exception as e:
        logging.warning(f"[Analyst synthesis] KB retrieval failed: {e}")

    fw_labels = ANALYST_FRAMEWORK_LABELS_CN if lang == "cn" else ANALYST_FRAMEWORK_LABELS_EN
    fw_order = ["business_model", "moat", "management", "margin_of_safety"]
    skipped = "(已跳过)" if lang == "cn" else "(Skipped)"

    answers_block = "\n\n".join(
        f"【{fw_labels[fw_order[i]]}】\n{request.answers[i] or skipped}"
        for i in range(min(len(request.answers), len(fw_order)))
    )
    feedbacks_block = "\n\n".join(
        f"【{fw_labels[fw_order[i]]} 反馈摘要】\n{request.feedbacks[i][:200] if i < len(request.feedbacks) else ''}"
        for i in range(min(len(request.answers), len(fw_order)))
    )

    if lang == "cn":
        user_msg = (
            f"【知识库原文摘录】\n{kb_context}\n\n"
            f"---\n\n【学员分析的公司】{request.company}\n\n"
            f"【学员的 4 框架回答】\n{answers_block}\n\n"
            f"---\n\n【各框架反馈摘要】\n{feedbacks_block}\n\n"
            f"请写这位学员的个人投资笔记。"
        )
    else:
        user_msg = (
            f"[Knowledge base excerpts]\n{kb_context}\n\n"
            f"---\n\n[Company] {request.company}\n\n"
            f"[Student's 4-framework answers]\n{answers_block}\n\n"
            f"---\n\n[Framework feedback summaries]\n{feedbacks_block}\n\n"
            f"Write the student's personal investment memo."
        )

    response = get_generation_gateway().complete(
        "long_synthesis",
        max_tokens=4096,
        system=ANALYST_SYNTHESIS_SYSTEM_CN if lang == "cn" else ANALYST_SYNTHESIS_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
    )

    return {"synthesis": response.text.strip(), "company": request.company}


@app.post("/api/digest")
async def digest(request: DigestRequest):
    """LLM call for daily business briefing — no RAG, just generation."""
    try:
        response = get_generation_gateway().complete(
            "daily_digest",
            max_tokens=2000,
            system=request.system,
            messages=[
                {"role": "user",   "content": request.prompt},
            ],
        )
        return {"content": response.text}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    from rag import query_knowledge_base
    result = query_knowledge_base(request.query, history=request.history)
    return result

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    logging.info(f"[RAG] Request received: {request.query[:80]!r}")
    from rag import stream_query_knowledge_base

    def generate():
        yield from stream_query_knowledge_base(request.query, history=request.history)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/tutor/stream")
async def tutor_stream(request: TutorRequest):
    logging.info(f"[Tutor] Request received: {request.message[:80]!r}")
    from tutor import stream_tutor_response

    def generate():
        yield from stream_tutor_response(
            request.message,
            history=request.history,
            curriculum_state=request.curriculum_state,
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ── Coach routes ─────────────────────────────────────────────────────────────
import uuid as _uuid
from datetime import date as _date
from database import init_db, get_db, CompanyArchive, UserState
from sqlalchemy.orm import Session
from fastapi import Depends

class CoachRequest(BaseModel):
    message: str
    history: list = []
    company: str = ""
    mode: str = "normal"
    onboarding_module: str = "模块一：商业模式"

class RecordRequest(BaseModel):
    company_id: str = ""
    company_name: str
    ticker: str = ""
    module_id: str = ""
    module_summary: str = ""
    skipped: bool = False
    status: str = "in_progress"
    conversation: list = []

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/coach", response_class=HTMLResponse)
async def coach_page():
    with open(frontend_dir / "coach.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/coach/stream")
async def coach_stream(request: CoachRequest):
    def generate():
        yield from stream_coach_response(
            request.message,
            history=request.history,
            company=request.company,
            mode=request.mode,
            onboarding_module=request.onboarding_module,
        )
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/api/coach/state")
async def get_state(db: Session = Depends(get_db), visitor: str = Depends(coach_visitor)):
    state = db.query(UserState).filter_by(id=visitor).first()
    if not state:
        return {"onboarding_completed": False, "onboarding_skipped": False, "onboarding_current_module": "1.1"}
    return {
        "onboarding_completed": state.onboarding_completed == "true",
        "onboarding_skipped": state.onboarding_skipped == "true",
        "onboarding_current_module": state.onboarding_current_module,
    }

@app.post("/api/coach/state")
async def update_state(payload: dict, db: Session = Depends(get_db), visitor: str = Depends(coach_visitor)):
    state = db.query(UserState).filter_by(id=visitor).first()
    if not state:
        state = UserState(id=visitor)
        db.add(state)
    if "onboarding_completed" in payload:
        state.onboarding_completed = str(payload["onboarding_completed"]).lower()
    if "onboarding_skipped" in payload:
        state.onboarding_skipped = str(payload["onboarding_skipped"]).lower()
    if "onboarding_current_module" in payload:
        state.onboarding_current_module = payload["onboarding_current_module"]
    db.commit()
    return {"ok": True}

@app.post("/api/coach/record")
async def save_record(request: RecordRequest, db: Session = Depends(get_db), visitor: str = Depends(coach_visitor)):
    company_id = request.company_id or request.company_name.lower().replace(" ", "_")
    archive = db.query(CompanyArchive).filter_by(company_id=f"{visitor}:{company_id}").first()
    if not archive:
        archive = CompanyArchive(
            company_id=f"{visitor}:{company_id}",
            company_name=request.company_name,
            ticker=request.ticker,
            first_analysis=str(_date.today()),
            last_updated=str(_date.today()),
            sessions=[],
        )
        db.add(archive)
    archive.last_updated = str(_date.today())
    sessions = list(archive.sessions or [])
    if not sessions or sessions[-1]["status"] == "completed":
        sessions.append({
            "session_id": str(_uuid.uuid4()),
            "date": str(_date.today()),
            "status": "in_progress",
            "modules_completed": [],
            "skipped_modules": [],
            "record": {},
            "conversation": request.conversation,
        })
    session = sessions[-1]
    if request.module_id:
        if request.skipped:
            if request.module_id not in session["skipped_modules"]:
                session["skipped_modules"].append(request.module_id)
        else:
            if request.module_id not in session["modules_completed"]:
                session["modules_completed"].append(request.module_id)
        session["record"][request.module_id] = request.module_summary
    session["status"] = request.status
    session["conversation"] = request.conversation
    archive.sessions = sessions
    db.commit()
    return {"ok": True, "company_id": company_id}

@app.get("/api/coach/companies")
async def get_companies(db: Session = Depends(get_db), visitor: str = Depends(coach_visitor)):
    archives = db.query(CompanyArchive).filter(CompanyArchive.company_id.startswith(f"{visitor}:")).all()
    result = []
    for a in archives:
        latest = a.sessions[-1] if a.sessions else {}
        result.append({
            "company_id": a.company_id.split(":", 1)[1],
            "company_name": a.company_name,
            "ticker": a.ticker,
            "last_updated": a.last_updated,
            "session_count": len(a.sessions),
            "modules_completed": latest.get("modules_completed", []),
            "skipped_modules": latest.get("skipped_modules", []),
        })
    return sorted(result, key=lambda x: x["last_updated"], reverse=True)

@app.get("/api/coach/company/{company_id}")
async def get_company(company_id: str, db: Session = Depends(get_db), visitor: str = Depends(coach_visitor)):
    archive = db.query(CompanyArchive).filter_by(company_id=f"{visitor}:{company_id}").first()
    if not archive:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return {
        "company_id": company_id,
        "company_name": archive.company_name,
        "ticker": archive.ticker,
        "first_analysis": archive.first_analysis,
        "last_updated": archive.last_updated,
        "sessions": archive.sessions,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
