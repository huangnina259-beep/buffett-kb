"""
RAG query engine: ChromaDB retrieval + Claude API generation.
Supports both blocking and streaming (SSE) response modes.
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import anthropic

SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR   = ROOT_DIR / "database"

COLLECTION_NAME = "buffett_kb"
EMBED_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"
CLAUDE_MODEL    = "claude-haiku-4-5-20251001"
TOP_K           = 8     # 6 was too few for rich conceptual questions
MAX_TOKENS      = 3000  # 2048 cut off detailed answers; 3000 is still fast

SYSTEM_PROMPT = """你是"复利国"价值投资知识库。

知识库来源：巴菲特致股东信（1977–2025）、查理·芒格著述、
Howard Marks备忘录、李录演讲与著作。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【核心定位】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
严谨专业，清晰易懂，可操作。
每个答案必须能落地到一个具体动作。
如果回答里出现"需要理解""需要判断"，
必须立刻追加"具体怎么理解/判断"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【语言一致性】（强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用与用户提问完全相同的语言回答。
中文问题→中文回答。
英文问题→英文回答，所有检索到的中文内容翻译为英文。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【问题分类与回答结构】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
收到问题后，先判断类型，再选择对应结构。

──────────────────────────
A. 概念解释类
──────────────────────────
触发："什么是X""X是什么意思""如何理解X"

结构（五层完整展开，不能省略任何一层）：

【第一层：定义轴】
用最简单的语言解释这个概念，不用术语。
给出一个正面例子和一个反面例子。

【第二层：机制轴】
解释它为什么是这样的。
写出完整的因果链：A → B → C。
说明这个逻辑在什么条件下不成立（边界条件）。

【第三层：验证轴】
我怎么知道一家真实的公司有/没有这个特征？
具体检验方法：看哪个数据、问哪个问题、找哪种证据。

【第四层：盲区触发】⚠️（最重要，不能省略）
主动列出以下三项：
1. 用户没有问到但同样重要的2-3个问题
2. 这个框架隐含的假设，用户可能没有注意到
3. 最聪明的反对者会用什么逻辑反驳这整个框架

【第五层：实践轴】
如果现在拿着一家真实公司来用这个框架，
第一个具体动作是什么？
精确到："打开财报，找到第X行数据，用它来判断Y"
不接受"理解商业模式"这种模糊的说法。

【强制出口】
「如果我研究___公司，我会用今天学到的内容
去检验___，因为___。」
如果用户填不出来，帮他找到是哪个环节断了。

──────────────────────────
B. 判断分析类
──────────────────────────
触发："为什么X""X是怎么想的""X为什么做Y"
"巴菲特/芒格/Marks/李录如何看待X"

结构：
- 背景：一句话说清楚发生了什么或问题的核心
- 核心判断：大师的观点，引用原文支撑
- 观点演变：随时间的变化（变化本身往往最有价值）
- 多大师分歧：如果多位大师看法不同，主动呈现

不需要五层，不需要强制出口填空。

──────────────────────────
C. 对比视角类
──────────────────────────
触发："X和Y有什么不同""从X视角看"
"如果X来判断""巴菲特和芒格对X的看法有什么差别"

结构：
- 各人视角：分别展开，每个视角锚定知识库原文
- 共同点：先讲共识
- 核心分歧：这是最有价值的部分，重点展开

不需要五层。

──────────────────────────
D. 操作方法类
──────────────────────────
触发："怎么X""如何X""用什么方法X"
"怎么读财报""如何计算内在价值"

结构（简化五层，重点在后三层）：
- 定义轴：可简短，一句话说清楚
- 验证轴：重点展开，具体到数据和操作
- 实践轴：重点展开，精确到具体动作
- 盲区触发：保留，不能省略
可省略：机制轴

──────────────────────────
E. 自研公司类
──────────────────────────
触发：用户明确说"我想分析XX公司"
"帮我看看XX值不值得投资"
或提到一家知识库未覆盖的具体公司名称。

用户问投资原则、概念解释等知识性问题时，
不使用此模式。

核心原则：不给买卖结论，引导用户用四层框架自己想清楚。
每层结束等用户回答再继续，绝对不一次性抛出所有问题。

第一层：读懂这门生意
「用一句话说：这家公司靠什么赚钱？
客户为什么付钱给它而不是给竞争对手？」

第二层：护城河的性质与宽度
「如果明天有个资金雄厚的竞争对手来抢客户，
这家公司最大的防线是什么？」
引导检验：品牌溢价 / 转换成本 / 网络效应 /
成本优势 / 监管许可
关键追问：「这条护城河是在变宽还是变窄？」

第三层：管理层是朋友还是陌生人
「过去五年，这家公司赚到的钱去哪了？」
引导看：再投资回报率 / 资本配置历史 / 股东利益导向

第四层：价格与价值的距离
只在前三层都想清楚之后才进入。
「你现在付的价格，买的是什么？
市场隐含了对它未来的什么预期？」

交互规则（强制）：
- 每次只呈现当前层，绝不提前透露下一层
- 用户回答后：认可做得好的地方（具体说），
  提出一个让他自己发现问题的追问
- 用户说得不准确时，不纠正，而是追问：
  「有意思。如果[用户判断]，那[挑战性问题]？」
- 每层只问一个问题，不用编号列表
- 第四层完成后最后一句固定：
  「买卖决定是你的，这个框架帮你把该想的都想到了。」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【引用规范】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 有原文支撑才说，没有就直接说"知识库里没有这方面的记录"
- 引用格式：只用 [来源N]，标签本身已显示作者和年份
- 知识不足时，用已有内容充分展开，
  不要主动声明"知识库没有完整分类"
- 推演时标注：「以下基于其一贯立场推演，知识库中无直接记录」

人物匹配原则（强制）：
- 用户问题中明确提到某位大师时，优先引用该大师的原话
- 引用其他大师对他方法的总结时，必须标注：
  「这是[B]对[A]方法的总结，不是[A]的原话」
- 禁止把[B]说的话当作[A]的观点直接呈现

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：诚实边界】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 直接说知识库里没有，禁止用"可能""大概"掩盖
- 知识库收录截至2025年，此后信息不在范围内

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【追问】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A/B/C/D类问题：每次回答结尾提供3个追问，
放在 <follow_ups></follow_ups> 标签内。
追问必须锚定在当前检索到的来源文档里，
只问有原材料能回答的问题。
E类问题：不使用此规则，
每层只问一个最能推动深入思考的问题。"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_collection():
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


TERM_TRANSLATIONS = {
    "护城河":   "economic moat",
    "安全边际": "margin of safety",
    "内在价值": "intrinsic value",
    "能力圈":   "circle of competence",
    "资本配置": "capital allocation",
    "市场先生": "Mr. Market",
    "浮存金":   "float",
    "留存收益": "retained earnings",
    "账面价值": "book value",
    "特许经营权": "franchise value",
}

def _translate_query(question: str) -> str:
    """Translate known Chinese investment terms, then strip remaining Chinese
    characters so ChromaDB gets a clean English query to match against
    English-language source documents."""
    q = question
    for zh, en in TERM_TRANSLATIONS.items():
        q = q.replace(zh, en)

    # Strip remaining Chinese/CJK characters and tidy up whitespace
    q_en = re.sub(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+', ' ', q)
    q_en = re.sub(r'\s+', ' ', q_en).strip()

    # Fallback: if stripping left nothing useful, use the translated-but-mixed version
    return q_en if len(q_en) >= 4 else q


AUTHOR_KEYWORDS = {
    "Warren Buffett":  ["巴菲特", "buffett"],
    "Charlie Munger":  ["芒格", "munger", "穷查理", "poor charlie"],
    "Howard Marks":    ["马克斯", "howard marks"],
    "Li Lu":           ["李录", "li lu"],
}

def _detect_author(question: str) -> Optional[str]:
    """Return canonical author name if question explicitly names one person."""
    q = question.lower()
    for author, keywords in AUTHOR_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return author
    return None


def _extract_search_params(question: str, history: list, client_api=None) -> tuple:
    """Extract year/doc_type/author via regex — no API call, zero added latency.
    search_query has known Chinese investment terms replaced with English equivalents
    so ChromaDB vector search matches English-language source documents better."""
    search_query = _translate_query(question)
    search_params = {"query": search_query, "year": None, "doc_type": None, "author": None}
    where_clause = None

    where = {}

    # Author: filter to the specific person being asked about
    author = _detect_author(question)
    if author:
        where["author"] = author
        search_params["author"] = author

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

    logging.info(f"[RAG] search_query: {search_query!r}")
    logging.info(f"[RAG] where_clause: {where_clause}")

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
        author_note  = f" | 作者: {meta['author']}" if meta.get("author") else ""
        section_note = f" — {meta['section']}" if meta.get("section") else ""
        year_note    = f" ({meta['year']})" if meta.get("year") else ""
        header       = f"[来源{i}] {meta['source_label']}{year_note}{author_note}{section_note}"
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
            "author":       meta.get("author", ""),
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


PRIMARY_AUTHORS   = {"Warren Buffett", "Charlie Munger"}
SECONDARY_AUTHORS = {"Li Lu", "Howard Marks"}


def _merge_results(*result_lists, top_k: int) -> dict:
    """Merge multiple ChromaDB result dicts, deduplicate by doc content, keep top_k."""
    seen = set()
    docs, metas, dists = [], [], []
    for r in result_lists:
        if not r["documents"] or not r["documents"][0]:
            continue
        for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
            key = doc[:120]  # fingerprint by first 120 chars
            if key not in seen:
                seen.add(key)
                docs.append(doc)
                metas.append(meta)
                dists.append(dist)
    # Sort by distance (ascending = more relevant) and trim
    combined = sorted(zip(dists, docs, metas), key=lambda x: x[0])[:top_k]
    if not combined:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    dists_out, docs_out, metas_out = zip(*combined)
    return {"documents": [list(docs_out)], "metadatas": [list(metas_out)], "distances": [list(dists_out)]}


def _log_chunks(results: dict, label: str):
    metas = results["metadatas"][0] if results["metadatas"] and results["metadatas"][0] else []
    dists = results["distances"][0] if results["distances"] and results["distances"][0] else []
    logging.info(f"[RAG] {label} → {len(metas)} chunks:")
    for i, (m, d) in enumerate(zip(metas, dists), 1):
        logging.info(f"[RAG]   [{i}] {m.get('source_file','?')} | author={m.get('author','?')} | year={m.get('year','?')} | dist={d:.4f}")


def _retrieve(search_query: str, where_clause, top_k: int, target_author: Optional[str] = None) -> dict:
    """Priority-aware retrieval.

    Case A — specific author requested (target_author set):
      1. Query with author filter.
      2. If < 3 results, supplement with secondary sources (no author filter).

    Case B — no specific author (target_author is None):
      1. Query primary authors (Buffett + Munger) for top_k results.
      2. If primary results < top_k, fill remaining slots from secondary
         authors (Li Lu, Marks) — keeps primary sources dominant.
      3. If still short, open to all sources.

    Year/doc_type filters from where_clause are preserved in both cases.
    """
    collection = _get_collection()

    # Extract non-author filters (year, doc_type) from where_clause
    base_filters = {}
    if where_clause:
        if "$and" in where_clause:
            for cond in where_clause["$and"]:
                if "author" not in cond:
                    base_filters.update(cond)
        elif "author" not in where_clause:
            base_filters = dict(where_clause)

    def _build_where(extra: dict) -> Optional[dict]:
        merged = {**base_filters, **extra}
        if not merged:
            return None
        if len(merged) == 1:
            return merged
        return {"$and": [{k: v} for k, v in merged.items()]}

    def _query(where=None, n=top_k):
        p = {
            "query_texts": [search_query],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            p["where"] = where
        try:
            return collection.query(**p)
        except Exception:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def _count(r):
        return len(r["documents"][0]) if r["documents"] and r["documents"][0] else 0

    # ── Case A: specific author requested ────────────────────────────────────
    if target_author:
        results = _query(_build_where({"author": target_author}))
        n = _count(results)
        if n < 3:
            supp = _query(_build_where({}), n=top_k)
            results = _merge_results(results, supp, top_k=top_k)
        if _count(results) == 0:
            results = _query(None)
        _log_chunks(results, f"Case A (author={target_author})")
        return results

    # ── Case B: no specific author — priority tiers ───────────────────────────
    primary_where = _build_where({"author": {"$in": list(PRIMARY_AUTHORS)}})
    logging.info(f"[RAG] tier1 where: {primary_where}")
    primary = _query(primary_where)
    n_primary = _count(primary)
    logging.info(f"[RAG] tier1 returned: {n_primary} chunks (top_k={top_k})")

    if n_primary >= top_k:
        logging.info("[RAG] no fallback needed")
        _log_chunks(primary, "Case B tier1 (primary only)")
        return primary

    need = top_k - n_primary
    logging.info(f"[RAG] tier1 short by {need}, querying tier2 (secondary authors)")
    secondary_where = _build_where({"author": {"$in": list(SECONDARY_AUTHORS)}})
    secondary = _query(secondary_where, n=need)
    n_secondary = _count(secondary)
    logging.info(f"[RAG] tier2 returned: {n_secondary} chunks")

    results = _merge_results(primary, secondary, top_k=top_k)
    if _count(results) >= 3:
        logging.info(f"[RAG] final total: {_count(results)} chunks (no tier3)")
        _log_chunks(results, "Case B tier1+2 (primary+secondary)")
        return results

    logging.info("[RAG] tier1+2 still short, triggering tier3 (all sources)")
    fallback = _query(_build_where({}), n=top_k)
    results = _merge_results(results, fallback, top_k=top_k)
    logging.info(f"[RAG] final total after tier3: {_count(results)} chunks")
    _log_chunks(results, "Case B tier3 (fallback)")
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
    target_author = search_params.get("author")

    # 2. Retrieve
    try:
        results = _retrieve(search_query, where_clause, top_k, target_author=target_author)
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
    target_author = search_params.get("author")

    try:
        results = _retrieve(search_query, where_clause, top_k, target_author=target_author)
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
