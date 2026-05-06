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

load_dotenv(Path(__file__).parent / ".env", override=True)  # Load API keys from .env if present

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


GYM_SYSTEM_CN = """你是复利国的价值投资导师。风格：像芒格一样直接，像巴菲特一样温和。

你的任务：基于提供的知识库原文，评估学员的案例分析回答。

反馈要求：
- 200-280字，聚焦最重要的1-2个概念
- 先肯定学员答对的部分（具体指出为什么对，不要空洞夸奖）
- 再指出遗漏或需要深化的地方
- **必须引用知识库原文**支撑你的每一个核心观点，格式：「原文」——作者/来源
- 如果知识库里没有直接相关原文，直接说"知识库里没有关于这点的直接记录"
- 不给分数
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

# Per-round search queries for RAG retrieval — maps case_id → list of queries (one per round)
GYM_ROUND_QUERIES = {
    "cocacola": [
        "Coca-Cola concentrate model bottler asset-light business free cash flow margins",
        "Coca-Cola brand moat consumer franchise competitive advantage durable",
        "capital allocation management Goizueta share buyback ROE shareholder returns",
        "Coca-Cola ROE return on equity free cash flow net margin financial metrics",
        "Coca-Cola intrinsic value margin of safety consumer brand valuation 1988",
    ]
}

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

    # Retrieve knowledge base context for this round
    kb_context = ""
    try:
        from rag import retrieve_context
        queries = GYM_ROUND_QUERIES.get(request.case_id, [])
        query = queries[request.round] if request.round < len(queries) else request.question
        kb_context, _ = retrieve_context(query, top_k=8)
    except Exception as e:
        logging.warning(f"[Gym] KB retrieval failed: {e}")

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

    client_ant = Anthropic(api_key=anthropic_key)
    response = client_ant.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=GYM_SYSTEM_CN if lang == "cn" else GYM_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        return json_lib.loads(text)
    except json_lib.JSONDecodeError:
        return {"feedback": text, "key_concepts": []}


SYNTHESIS_SYSTEM_CN = """你是复利国的价值投资导师。学员刚完成了一个完整的五轮案例分析训练。

你的任务：基于知识库原文和学员的全部回答+反馈，写一份有深度的综合投资分析。

格式要求：
## 投资结论
用2-3句话给出这家公司作为投资标的的核心判断，必须引用知识库原文支撑。

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
## Investment Verdict
2-3 sentences on this company as an investment. Must cite knowledge base.

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
    import json as json_lib
    from anthropic import Anthropic

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY not set"}, status_code=500)

    lang = request.language

    # Broad KB retrieval covering the full case
    kb_context = ""
    try:
        from rag import retrieve_context
        case_queries = {
            "cocacola": "Coca-Cola Buffett 1988 investment brand moat capital allocation intrinsic value consumer franchise",
        }
        query = case_queries.get(request.case_id, request.case_id)
        kb_context, _ = retrieve_context(query, top_k=10)
    except Exception as e:
        logging.warning(f"[Gym synthesis] KB retrieval failed: {e}")

    round_names_cn = ["商业模式", "经济护城河", "管理层评估", "财务分析", "估值与安全边际"]
    round_names_en = ["Business Model", "Economic Moat", "Management", "Financial Analysis", "Valuation"]
    round_names = round_names_cn if lang == "cn" else round_names_en

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

    client_ant = Anthropic(api_key=anthropic_key)
    response = client_ant.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYNTHESIS_SYSTEM_CN if lang == "cn" else SYNTHESIS_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
    )

    return {"synthesis": response.content[0].text.strip()}


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
    import json as json_lib
    from anthropic import Anthropic

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY not set"}, status_code=500)

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

    client_ant = Anthropic(api_key=anthropic_key)
    response = client_ant.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=ANALYST_FEEDBACK_SYSTEM_CN if lang == "cn" else ANALYST_FEEDBACK_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        return json_lib.loads(text)
    except json_lib.JSONDecodeError:
        return {"feedback": text, "key_concepts": []}


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
    from anthropic import Anthropic

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return JSONResponse(content={"error": "ANTHROPIC_API_KEY not set"}, status_code=500)

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

    client_ant = Anthropic(api_key=anthropic_key)
    response = client_ant.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1400,
        system=ANALYST_SYNTHESIS_SYSTEM_CN if lang == "cn" else ANALYST_SYNTHESIS_SYSTEM_EN,
        messages=[{"role": "user", "content": user_msg}],
    )

    return {"synthesis": response.content[0].text.strip(), "company": request.company}


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
