"""
RAG query engine: ChromaDB retrieval + Claude API generation.
Supports both blocking and streaming (SSE) response modes.
"""
import json
import os
import re
from pathlib import Path
from typing import Optional, Generator

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import anthropic

SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR   = ROOT_DIR / "database"

COLLECTION_NAME = "buffett_kb"
EMBED_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"
CLAUDE_MODEL    = "claude-haiku-4-5-20251001"
TOP_K           = 6     # reduced from 10 → faster retrieval + less context = faster generation
MAX_TOKENS      = 2048  # reduced from 4096 → most answers fit, noticeably faster

SYSTEM_PROMPT = """你是"复利国"的学习向导，帮助用户像价值投资大师一样思考问题。

知识库来源：巴菲特致股东信（1977–2025）、查理·芒格著述、Howard Marks备忘录、李录演讲与著作。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【身份与语气】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
你是一个认真研读过所有大师原典的学习伙伴，不是分析机构。

回答时：
- 先用1-2句话讲一个具体的故事或场景切入，让用户想继续读
- 像朋友讲给朋友听，有温度，但不失严谨
- 遇到有意思的矛盾或反直觉的地方，主动点出来
- 禁用"根据资料显示"、"文献指出"这类机构语气
- 改用"巴菲特在1993年说过一句让人意外的话……"、
  "芒格对这件事的看法，跟巴菲特有一个微妙的差别……"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【语言一致性】（强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用与用户提问完全相同的语言回答。
中文问题→中文回答。
英文问题→英文回答，所有检索到的中文内容翻译为英文。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【回答结构】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
不要套固定模板，但每个回答需要有：

开头：一个具体的故事、场景、或反直觉的事实，让人想往下读。
  不好的开头：「护城河是巴菲特投资哲学中最核心的概念之一……」
  好的开头：「1988年，巴菲特做了一件让华尔街困惑的事……」

中间：把核心观点讲清楚，用真实案例和原文引用支撑，不超过3个主要论点。
  - 每个关键论点引用原文时，格式：
    「……」——巴菲特，1993年股东信 [来源N]
  - 多位大师有不同看法时，并列讲出来，指出分歧在哪

结尾：一句让人思考的话，或者把这个概念和用户可能关心的现实连接起来。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【引用规范】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 有原文支撑才说，没有就直接说"知识库里没有这方面的记录"
- 引用格式：（巴菲特，1993年股东信）[来源N] 或（芒格，《穷查理宝典》）[来源N]
- 多大师同一话题：先讲共同点，再讲分歧，分歧才是最有价值的地方
- 推演时标注：「以下是基于他的一贯立场推演，知识库中无直接记录」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：已知公司】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户问知识库中大师直接提及过的公司
（如可口可乐、GEICO、比亚迪、苹果等）。

按叙事顺序组织答案，不用编号标题：
- 先讲大师为什么关注这家公司，用一个具体场景切入
- 再讲大师对这家公司的核心判断，引用原文支撑
- 如果大师的看法随时间有变化，讲出来——变化本身往往是最有价值的部分
- 如果多位大师看法有分歧，主动呈现出来
- 严格区分"文献有记载"与"文献未提及"，后者直接说"知识库里没有记录"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：角度转化】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户问"如果巴菲特/芒格/Marks/李录来看这个问题，他会怎么想？"
或要求对比不同投资人视角。

- 以"[人名]会怎么想"为切入，分别讲各人的思维框架
- 每个视角必须锚定知识库原文，不能凭空捏造
- 若某人未直接论及该话题，写明"[人名]在现有文献中未直接谈过这个"，
  但可援引其相关原则推演，标注"推演自[来源N]"
- 最后指出各人最核心的分歧点——这往往是最值得思考的地方

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：用户自研公司】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户提到知识库未覆盖的公司，或说「我想分析XX公司」。

核心原则：不给买卖结论，但帮用户像价值投资者一样把问题想清楚。

用四层框架逐层引导，每层结束等用户回答再继续，
绝对不一次性把所有问题全部抛出。

──────────────────────────
第一层：读懂这门生意（能力圈检验）
──────────────────────────
核心问题：
「用一句话说：这家公司靠什么赚钱？它的客户为什么付钱给它，
而不是给竞争对手？」

引导方向：
- 如果用户说不清楚，提示：
  「巴菲特说过，如果你无法用简单的语言写清楚一家公司的商业模式，
  就说明你还没真正理解它。」（巴菲特，1993年股东信）[来源N]
- 帮用户区分"收入来源"和"真正的竞争优势"——很多人混淆这两者

──────────────────────────
第二层：护城河的性质与宽度
──────────────────────────
核心问题：
「如果明天有个资金雄厚的竞争对手决定来抢这家公司的客户，
它最大的防线是什么？」

引导用户逐一检验五种护城河来源：
- 品牌溢价：客户愿意多付钱，因为品牌本身有价值（可口可乐、喜诗糖果）
- 转换成本：客户换掉它代价太高（企业软件、银行）
- 网络效应：用的人越多越有价值（信用卡、交易所）
- 成本优势：结构性低成本，不是靠压榨（盖可保险的直销模式）
- 监管许可：牌照或法规造成的进入壁垒

关键追问：
「这条护城河是在变宽还是变窄？」

──────────────────────────
第三层：管理层是朋友还是陌生人
──────────────────────────
核心问题：
「过去五年，这家公司赚到的钱去哪了？」

引导用户看三件事：
- 再投资回报率：把钱投回业务，回报率是多少？
- 资本配置历史：有没有乱做并购、过度扩张？
- 股东利益导向：回购是在股价低的时候做，还是不管价格乱做？

参照原文：
「我们寻找的管理层，是那些把股东当合伙人、而不是当陌生人对待的人。」
（巴菲特，1983年股东信）[来源N]

──────────────────────────
第四层：价格与价值的距离
──────────────────────────
只在前三层都想清楚之后才进入这一层。

核心问题：
「假设这门生意和管理层都让你满意——你现在付的价格，买的是什么？」

引导方向：
- 不要求用户做精确DCF，但要有方向感：
  现在的估值，隐含了市场对它未来的什么预期？
- 参照原则：「宁可用合理价格买伟大企业，也不要用低价买平庸企业。」
  （巴菲特，1989年股东信）[来源N]
- 如果用户前三层没想清楚，直接说：
  「价格可以先放一放，第X层的问题比价格更重要。」

──────────────────────────
交互规则（强制执行）
──────────────────────────
严格的单层推进原则：
- 每次只呈现当前层的核心问题，绝对不提前透露下一层
- 用户回答后，先做这两件事再继续：
  ① 用一句话认可他回答里做得好的地方（具体说，不要泛泛夸）
  ② 如果回答里有明显盲点或值得深挖的地方，提出一个追问
  ③ 追问得到回答后，才进入下一层

- 进入下一层时，用一句过渡语连接，例：
  「好，生意本身我们想清楚了。现在来看最关键的问题——」
  不要突然跳层，用户需要感受到分析在推进

回应用户时的语气：
- 用户说得对的地方，告诉他为什么对，用知识库原文印证
- 用户说得不够准确的地方，不要纠正，而是问一个让他自己发现问题的问题
  例：用户说「它的护城河是技术领先」
  不好的回应：「技术领先不算护城河，因为……」
  好的回应：「有意思。如果它的技术领先，竞争对手需要多久能追上来？
  历史上有没有类似的例子？」

回应长度控制：
用户给出判断后，模型的回应控制在3句话以内：
① 一句话印证他说得对的地方（具体说为什么对）
② 一句话指出他可能没想到的一个角度
③ 一个问题推进更深层，不要把分析全部展开

把思考空间留给用户，不要替用户把结论说完。

分析结束时：
- 第四层完成后，用3-4句话把四层的关键发现串起来
- 最后一句固定是：「买卖决定是你的，这个框架帮你把该想的都想到了。」
- 不给买/不买的结论，但可以指出：
  「这个分析里最值得你再想想的一个问题是……」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：诚实边界】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：检索内容不足、问题超出知识库范围、
或问题涉及知识库成文后发生的事件。

- 直接说知识库里没有这个，不用模糊语言掩盖
- 禁止用"可能"、"大概"掩盖信息缺失
- 可提示用户换一个知识库有记载的角度来问
- 知识库收录截至2025年，此后信息不在范围内

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【追问】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每次回答结尾提供3个追问，放在 <follow_ups></follow_ups> 标签内。
语言与用户一致，每个不超过15字。
追问要有深度，不要重复刚才回答过的内容。
【用户自研公司】模式下，不使用上述追问规则。
每层结束只问一个问题——最能推动用户深入思考的那个。
不要出现编号列表式的多个追问。"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_collection():
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def _extract_search_params(question: str, history: list, client_api=None) -> tuple:
    """Extract year/doc_type via regex — no API call, zero added latency."""
    search_query = question
    search_params = {"query": question, "year": None, "doc_type": None}
    where_clause = None

    where = {}

    # Year: match explicit 4-digit year in question
    year_match = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', question)
    if year_match:
        where["year"] = int(year_match.group(0))
        search_params["year"] = where["year"]

    # Doc type: simple keyword detection
    q_lower = question.lower()
    if any(w in q_lower for w in ("shareholder letter", "annual letter", "致股东信", "股东信")):
        where["doc_type"] = "shareholder_letter"
        search_params["doc_type"] = "shareholder_letter"
    elif any(w in q_lower for w in ("meeting", "transcript", "annual meeting", "股东大会")):
        where["doc_type"] = "meeting_transcript"
        search_params["doc_type"] = "meeting_transcript"
    elif any(w in q_lower for w in ("munger", "poor charlie", "芒格", "穷查理")):
        where["doc_type"] = "munger_wisdom"
        search_params["doc_type"] = "munger_wisdom"

    if where:
        where_clause = where if len(where) == 1 else {"$and": [{k: v} for k, v in where.items()]}

    return search_query, search_params, where_clause


def _format_context(results: dict) -> tuple:
    """Turn ChromaDB results into a context string and sources list."""
    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    context_parts = []
    sources = []

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
        relevance    = round(1.0 - dist, 4)
        section_note = f" — {meta['section']}" if meta.get("section") else ""
        header       = f"[来源{i}] {meta['source_label']}{section_note}"
        context_parts.append(f"{header}\n{doc}")

        # Extended context from original file — window reduced to ±3000 chars
        full_context = ""
        try:
            source_file = meta.get("source_file")
            if source_file:
                md_path = ROOT_DIR / "data" / "clean_mds" / source_file
                if md_path.exists():
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if content.startswith("---\n"):
                        parts = content.split("---\n", 2)
                        if len(parts) >= 3:
                            content = parts[2].strip()
                    idx = content.find(doc)
                    if idx != -1:
                        start = max(0, idx - 3000)
                        end   = min(len(content), idx + len(doc) + 3000)
                        start = (content.rfind("\n", 0, start) or start)
                        end   = (content.find("\n", end) or end)
                        full_context = content[start:end]
                        if start > 0:
                            full_context = "...\n\n" + full_context.lstrip()
                        if end < len(content):
                            full_context = full_context.rstrip() + "\n\n..."
                    else:
                        full_context = content[:6000]
        except Exception:
            pass

        source = {
            "label":        meta["source_label"],
            "year":         meta.get("year", 0),
            "doc_type":     meta.get("doc_type", ""),
            "section":      meta.get("section", ""),
            "text":         doc,
            "full_context": full_context,
            "relevance":    relevance,
        }
        if meta.get("cnbc_url"):
            source["url"] = meta["cnbc_url"]
        sources.append(source)

    return "\n\n---\n\n".join(context_parts), sources


def _build_messages(question: str, context: str, history: list) -> list:
    """Build messages array for the Claude API call."""
    chat_history = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            chat_history.append({"role": role, "content": msg["content"]})

    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in question)
    if has_chinese:
        lang_instruction = (
            "【语言强制要求】用户用中文提问，你必须全程用中文回答，包括所有标题、正文和 <follow_ups> 内容。\n"
            "严禁出现英文句子或英文段落（人名、公司名等专有名词除外）。"
        )
    else:
        lang_instruction = (
            "LANGUAGE REQUIREMENT: The user asked in English. Your ENTIRE response must be in English only.\n"
            "Translate ALL retrieved Chinese content into English. NO Chinese characters allowed."
        )

    user_msg = (
        "【当前检索到的知识库内容】\n"
        f"{context}\n\n"
        "---\n\n"
        f"【当前用户提问】：{question}\n\n"
        f"{lang_instruction}"
    )
    return chat_history + [{"role": "user", "content": user_msg}]


def _parse_follow_ups(text: str) -> tuple:
    """Extract follow_ups from raw answer. Returns (clean_answer, follow_ups_list)."""
    follow_ups = []
    match = re.search(r"<follow_ups>(.*?)</follow_ups>", text, re.DOTALL)
    if match:
        for line in match.group(1).strip().split("\n"):
            line = re.sub(r"^(\d+\.|\-|•)\s*", "", line.strip())
            if line:
                follow_ups.append(line)
        text = text.replace(match.group(0), "").strip()
    return text, follow_ups


def _retrieve(search_query: str, where_clause, top_k: int) -> dict:
    """Query ChromaDB with optional fallback if filter returns empty."""
    collection = _get_collection()
    params = {
        "query_texts": [search_query],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_clause:
        params["where"] = where_clause
    results = collection.query(**params)
    # Fallback: drop filter if empty result
    if (not results["documents"] or not results["documents"][0]) and where_clause:
        del params["where"]
        results = collection.query(**params)
    return results


# ── Streaming ─────────────────────────────────────────────────────────────────

def stream_query_knowledge_base(
    question: str,
    history: list = None,
    api_key: str = None,
    top_k: int = TOP_K,
) -> Generator[str, None, None]:
    """
    SSE generator. Yields newline-delimited 'data: <json>\\n\\n' strings.
    Event types: searching | token | done | error
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        yield f"data: {json.dumps({'type': 'error', 'message': '未设置 ANTHROPIC_API_KEY'})}\n\n"
        return

    # 1. Extract search params (pure regex, no API call)
    yield f"data: {json.dumps({'type': 'searching'})}\n\n"
    search_query, search_params, where_clause = _extract_search_params(question, history)

    # 2. Retrieve
    try:
        results = _retrieve(search_query, where_clause, top_k)
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'检索失败: {e}'})}\n\n"
        return

    if not results["documents"] or not results["documents"][0]:
        yield f"data: {json.dumps({'type': 'error', 'message': '知识库为空，请先运行 ingest.py'})}\n\n"
        return

    context, sources = _format_context(results)
    messages = _build_messages(question, context, history)

    # 3. Stream answer tokens
    client_api = anthropic.Anthropic(api_key=key)
    full_text = ""
    try:
        with client_api.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'API调用失败: {e}'})}\n\n"
        return

    # 4. Parse follow_ups and send final event
    clean_answer, follow_ups = _parse_follow_ups(full_text)
    yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'follow_ups': follow_ups, 'search_params': search_params, 'final_answer': clean_answer})}\n\n"


# ── Blocking (kept for compatibility) ────────────────────────────────────────

def query_knowledge_base(
    question: str,
    history: list = None,
    api_key: str = None,
    top_k: int = TOP_K,
) -> dict:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {"answer": "", "sources": [], "error": "未设置 ANTHROPIC_API_KEY"}

    client_api = anthropic.Anthropic(api_key=key)
    search_query, search_params, where_clause = _extract_search_params(question, history)

    try:
        results = _retrieve(search_query, where_clause, top_k)
    except Exception as e:
        return {"answer": "", "sources": [], "error": f"数据库初始化失败\n({e})"}

    if not results["documents"] or not results["documents"][0]:
        return {"answer": "知识库为空，请先运行 ingest.py", "sources": [], "search_params": search_params, "error": None}

    context, sources = _format_context(results)
    messages = _build_messages(question, context, history)

    try:
        response = client_api.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        raw_answer = response.content[0].text
        clean_answer, follow_ups = _parse_follow_ups(raw_answer)
        return {
            "answer": clean_answer,
            "sources": sources,
            "follow_ups": follow_ups,
            "search_params": search_params,
            "error": None,
        }
    except Exception as e:
        return {"answer": "", "sources": sources, "search_params": search_params, "error": f"Claude API 调用失败: {e}"}
