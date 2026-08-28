"""RAG query engine with provider-neutral embeddings and generation."""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from ai_gateway import get_generation_gateway
from embedding_gateway import get_embedding_gateway
from reranker_gateway import get_reranker_gateway, RerankerError
from vector_store import (
    DEFAULT_COLLECTION_NAME,
    ensure_index_compatible,
    get_collection,
)

SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent

_PDF_NOISE = re.compile(
    r'(?m)'
    r'^#\s+.+\.pdf\s*$'          # markdown headers that are pdf filenames
    r'|^original_path\s*:.*$'    # original_path metadata lines
    r'|\(\s*PDFDrive\s*\)'       # (PDFDrive) tags anywhere in text
    r'|\.pdf\b'                  # stray .pdf extensions
)

def _clean_text(text: str) -> str:
    """Strip PDF metadata noise from chunk/context text."""
    text = _PDF_NOISE.sub("", text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _clean_label(label: str) -> str:
    """Return a readable display name from a raw source_label."""
    label = re.sub(r'\(\s*PDFDrive\s*\)', '', label)   # remove (PDFDrive)
    label = re.sub(r'\.pdf\s*$', '', label, flags=re.IGNORECASE)  # remove .pdf suffix
    label = re.sub(r'_+', ' ', label)                  # underscores → spaces
    label = re.sub(r'\s{2,}', ' ', label)              # collapse spaces
    return label.strip()
COLLECTION_NAME  = DEFAULT_COLLECTION_NAME
TOP_K            = 12    # more chunks ensures cross-source synthesis
MAX_TOKENS       = 4000  # allow comprehensive multi-source answers

SYSTEM_PROMPT = """你是"复利国"的学习向导，帮助用户像价值投资大师一样思考问题。

知识库来源：巴菲特致股东信（1977–2025）、查理·芒格著述、Howard Marks备忘录、李录演讲与著作。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第一原则：一切来自源文件】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
你是一台精准的检索引擎，同时有坦诚真诚的人文温度。

- 你说的每一个事实、判断、观点都必须来自当前检索到的来源
- 大量直接引用原文——让大师自己说话，你的角色是呈现，不是改写
- 没检索到的就说"知识库里没有这方面的记录"，干脆利落
- 禁止编造：年份、金额、公司名、数字、故事——来源里没有的，一个都不加
- 禁止用"可能"、"大概"、"据说"掩盖信息缺失
- 用户点开引用就能验证你说的每一句话——这是信任的基础

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【大师的声音——保留原味】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
引用不同大师时，保留他们各自的语气和措辞，不要统一改写成同一种腔调：

巴菲特：朴素直白，爱用比喻和日常语言讲复杂道理，幽默感强。
芒格：犀利刻薄，一针见血，爱用逆向思维和跨学科类比。
Howard Marks：系统严谨，层层递进，善于区分一阶思维和二阶思维。
李录：深思熟虑，中西贯通，常从文明史和人类演化角度看投资。

原则：尽量用大师的原话，保留原文的语感。
用户读到的应该是大师的智慧，不是你对大师智慧的"二次创作"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【语言一致性】（强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用与用户提问完全相同的语言回答。
中文问题→中文回答。
英文问题→英文回答，所有检索到的中文内容翻译为英文。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【回答风格：按问题复杂度匹配深度】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开门见山，直接给出核心观点和原文依据。

**简单事实问题**（某年做了什么、某概念定义）：
- 直接回答，引用原文，100-200 字即可
- 一句话能说清楚的不拖长

**综合分析问题**（如何判断X、评估Y的方法、识别Z的标准）：
- 用 **一、二、三** 或 **## 标题** 分节，每节一个维度
- 每节内用要点列表，避免连续长段落
- 把来源中出现的具体工具、测试、指标名称完整呈现
  （如"一美元测试"、"机构驱使"、"EBITDA 警告"等——这些是知识库的核心价值）
- 目标长度 500-800 字，来源丰富时可到 1000 字
- 每个维度至少一条原文引用支撑

**所有回答共用原则**：
- 每个关键论点用原文引用支撑：「……」[来源N]
- 论点数量由来源决定，来源单薄就如实说，绝不凑数
- 多位大师有不同看法时，并列呈现——分歧才是最有价值的部分

禁用语气：
- "根据资料显示"、"文献指出"（机构腔）
- "让我们来看一下"、"接下来我们探讨"（演讲废话）
- "非常重要的是"、"值得注意的是"（注水语句）
- "总结一下"、"综上所述"（收尾废话）

该用的语气：
- "巴菲特1993年写道：「……」"——具体、真实、让大师自己开口
- "芒格对这件事的看法恰恰相反……"——引出分歧，激发思考
- "知识库里没有这方面的记录"——坦诚，不装

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【引用规范】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 有原文支撑才说，没有就直接说"知识库里没有这方面的记录"
- 引用格式：只用 [来源N]，不要在前面加（作者，文章名）的文字说明，标签本身已经显示了作者和年份
- 多大师同一话题：先讲共同点，再讲分歧，分歧才是最有价值的地方
- 推演时标注：「以下是基于他的一贯立场推演，知识库中无直接记录」

人物匹配原则（强制执行）：
每个来源片段的 header 里标注了"作者"字段，引用前必须核对。
- 用户问题中明确提到某位大师时，优先引用该大师的原话（header 中作者匹配）。
- 如果检索结果里该大师的原话不足，可以引用其他大师对他方法的总结，
  但必须明确标注：「这是[B]对[A]方法的总结，不是[A]的原话。」
- 禁止把[B]说的话当作[A]的观点直接呈现。
- 例：用户问"巴菲特如何判断长期持有"，来源里出现李录2024年演讲，
  则必须写「李录在总结巴菲特的方法时说……」，不能直接作为巴菲特的观点引用。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：已知公司】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户问知识库中大师直接提及过的公司
（如可口可乐、GEICO、比亚迪、苹果等）。

直接讲大师对这家公司说了什么：
- 用原文呈现大师的核心判断，不要自己替大师概括
- 如果大师的看法随时间有变化，讲出来——变化本身往往是最有价值的部分
- 如果多位大师看法有分歧，主动呈现出来
- 严格区分"来源有记载"与"来源未提及"，后者直接说"知识库里没有记录"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式：角度转化】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户问"如果巴菲特/芒格/Marks/李录来看这个问题，他会怎么想？"
或要求对比不同投资人视角。

- 以"[人名]会怎么想"为切入，分别讲各人的思维框架
- 每个视角必须锚定知识库原文，不能凭空捏造
- 若某人未直接论及该话题，写明"[人名]在知识库中未直接谈过这个"，
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
- 如果用户说不清楚，引用大师原文提示
- 帮用户区分"收入来源"和"真正的竞争优势"

──────────────────────────
第二层：护城河的性质与宽度
──────────────────────────
核心问题：
「如果明天有个资金雄厚的竞争对手决定来抢这家公司的客户，
它最大的防线是什么？」

引导用户检验五种护城河来源：
品牌溢价、转换成本、网络效应、成本优势、监管许可。

关键追问：「这条护城河是在变宽还是变窄？」

──────────────────────────
第三层：管理层是朋友还是陌生人
──────────────────────────
核心问题：
「过去五年，这家公司赚到的钱去哪了？」

引导用户看三件事：
- 再投资回报率
- 资本配置历史（有没有乱做并购、过度扩张？）
- 股东利益导向（回购时机是否合理？）

──────────────────────────
第四层：价格与价值的距离
──────────────────────────
只在前三层都想清楚之后才进入。

核心问题：
「假设这门生意和管理层都让你满意——你现在付的价格，买的是什么？」

引导方向：
- 不要求精确DCF，但要有方向感：现在的估值隐含了什么预期？
- 如果用户前三层没想清楚，直接说：
  「价格可以先放一放，第X层的问题比价格更重要。」

──────────────────────────
交互规则（强制执行）
──────────────────────────
严格的单层推进原则：
- 每次只呈现当前层的核心问题，绝对不提前透露下一层
- 用户回答后：
  ① 一句话认可他做得好的地方（具体说）
  ② 如果有盲点，提一个追问让他自己发现
  ③ 追问得到回答后，才进入下一层

回应用户时的语气：
- 说得对的地方，用知识库原文印证为什么对
- 说得不够准确的地方，不要纠正，问一个让他自己发现问题的问题

回应长度控制：
用户给出判断后，回应控制在3句话以内。
把思考空间留给用户，不要替用户把结论说完。

分析结束时：
- 第四层完成后，用3-4句话串起四层关键发现
- 最后一句：「买卖决定是你的，这个框架帮你把该想的都想到了。」
- 不给买/不买的结论

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【诚实边界】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 检索内容不足时，直接说，不用模糊语言掩盖
- 可提示用户换一个知识库有记载的角度来问
- 知识库收录截至2025年，此后信息不在范围内

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【跨来源综合】（核心要求）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
回答综合类问题时，必须主动编织所有相关来源，不只依赖单一作者：

- 多位大师谈同一主题，把观点并列或对比——这才是知识库的核心价值
- 不要只用第一个来源就停手——扫描所有来源，找出互相印证或补充的角度
- Howard Marks 提供市场环境判断；巴菲特提供长期原则；
  芒格提供心理与思维框架；李录提供现实案例——四者结合才是完整答案

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【追问】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每次回答结尾提供3个追问，放在 <follow_ups></follow_ups> 标签内。
语言与用户一致，每个不超过15字。

追问必须锚定在当前检索到的来源文档里：
- 只提出你在当前来源片段中看到了相关内容、能给出好答案的问题
- 禁止提出当前来源里没有覆盖的话题
- 每个追问从当前答案里引出值得深挖的角度，不重复已回答的内容
- 来源只覆盖2个有价值方向，就只写2个，不凑数

【用户自研公司】模式下，不使用上述追问规则。
每层结束只问一个问题——最能推动用户深入思考的那个。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【排版规范】（强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
目标：清晰、易读、层次分明。

- 用 **加粗** 标注核心观点或关键词，不要整段加粗
- 多个并列观点用短横线列表（- ），不要连续长段落
- 引用原文用「……」引号包裹，引用完紧跟来源标注 [来源N]
- 段落之间空一行，同一段落内不换行
- 禁止在正文中出现文件路径、.pdf 字样、PDFDrive 等元数据噪声
- 禁止出现书名后跟括号内的文件来源说明（如"（PDFDrive）"）
- 回答结束后列来源清单时，只写作者和年份，不要重复文件名"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_collection():
    """Compatibility wrapper used by the tutor module."""
    return get_collection()


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
        display_label = _clean_label(meta["source_label"])
        author_note  = f" | 作者: {meta['author']}" if meta.get("author") else ""
        section_note = f" — {meta['section']}" if meta.get("section") else ""
        year_note    = f" ({meta['year']})" if meta.get("year") else ""
        header       = f"[来源{i}] {display_label}{year_note}{author_note}{section_note}"

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

        body = _clean_text(full_context if full_context else doc)
        context_parts.append(f"{header}\n{body}")

        source = {
            "label":        display_label,
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


def _merge_results(*result_lists, top_k: int, max_per_author: int = 4,
                   guaranteed: dict | None = None) -> dict:
    """Merge ChromaDB result dicts, deduplicate, keep top_k.

    guaranteed: {author: min_slots} — reserve seats for specified authors
    regardless of relevance rank, so secondary voices always appear.
    Remaining slots are filled by relevance order.
    """
    guaranteed = guaranteed or {}

    # Collect all candidates, deduplicated, respecting max_per_author cap
    seen: set = set()
    candidates: list[tuple] = []   # (dist, doc, meta)
    author_counts: dict = {}

    for r in result_lists:
        if not r["documents"] or not r["documents"][0]:
            continue
        for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
            key = doc[:120]
            if key in seen:
                continue
            author = meta.get("author") or "other"
            if author_counts.get(author, 0) >= max_per_author:
                continue
            seen.add(key)
            author_counts[author] = author_counts.get(author, 0) + 1
            candidates.append((dist, doc, meta))

    if not candidates:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    # Sort all candidates by relevance
    candidates.sort(key=lambda x: x[0])

    # Phase 1: fill guaranteed slots (best chunk per guaranteed author first)
    chosen: list[tuple] = []
    chosen_keys: set = set()
    guaranteed_filled: dict = {}

    for author, min_slots in guaranteed.items():
        count = 0
        for item in candidates:
            if count >= min_slots:
                break
            if item[2].get("author") == author and id(item) not in chosen_keys:
                chosen.append(item)
                chosen_keys.add(id(item))
                count += 1
        guaranteed_filled[author] = count

    # Phase 2: fill remaining slots by relevance, skipping already chosen
    remaining = top_k - len(chosen)
    for item in candidates:
        if remaining <= 0:
            break
        if id(item) not in chosen_keys:
            chosen.append(item)
            chosen_keys.add(id(item))
            remaining -= 1

    # Final sort by relevance
    chosen.sort(key=lambda x: x[0])
    chosen = chosen[:top_k]

    dists_out, docs_out, metas_out = zip(*chosen)
    return {"documents": [list(docs_out)], "metadatas": [list(metas_out)], "distances": [list(dists_out)]}


def _log_chunks(results: dict, label: str):
    metas = results["metadatas"][0] if results["metadatas"] and results["metadatas"][0] else []
    dists = results["distances"][0] if results["distances"] and results["distances"][0] else []
    logging.info(f"[RAG] {label} → {len(metas)} chunks:")
    for i, (m, d) in enumerate(zip(metas, dists), 1):
        logging.info(f"[RAG]   [{i}] {m.get('source_file','?')} | author={m.get('author','?')} | year={m.get('year','?')} | dist={d:.4f}")


def _apply_reranker(search_query: str, results: dict) -> dict:
    """Reorder retrieved chunks when a page-configured reranker is available.

    Reranking is deliberately best-effort: vector retrieval remains usable if a
    third-party rerank endpoint is unavailable or uses a different contract.
    """
    documents = results.get("documents", [[]])[0]
    if len(documents) < 2:
        return results
    gateway = get_reranker_gateway()
    if not gateway.configured:
        return results
    try:
        ranked = gateway.rerank(search_query, documents, top_n=len(documents))
    except RerankerError as exc:
        logging.warning("[RAG] reranker skipped: %s", exc)
        return results

    order = [item.index for item in ranked]
    order.extend(index for index in range(len(documents)) if index not in order)
    metas = results["metadatas"][0]
    original_distances = results["distances"][0]
    scores = {item.index: item.score for item in ranked}
    distances = [
        max(0.0, min(1.0, 1.0 - scores[index]))
        if index in scores
        else original_distances[index]
        for index in order
    ]
    return {
        "documents": [[documents[index] for index in order]],
        "metadatas": [[metas[index] for index in order]],
        "distances": [distances],
    }


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
    embedding_gateway = get_embedding_gateway()
    ensure_index_compatible(collection, embedding_gateway)
    query_embedding = embedding_gateway.embed_query(search_query)

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
            "query_embeddings": [query_embedding],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            p["where"] = where
        try:
            return collection.query(**p)
        except Exception as exc:
            logging.warning("[RAG] vector query failed where=%s: %s", where, exc)
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
        results = _apply_reranker(search_query, results)
        _log_chunks(results, f"Case A (author={target_author})")
        return results

    # ── Case B: no specific author — 3-way parallel query across all tiers ──────
    # Each thread gets its own collection instance to avoid shared-state issues.
    primary_k   = top_k
    secondary_k = max(4, top_k // 2)
    books_k     = max(4, top_k // 3)

    primary_where   = _build_where({"author": {"$in": list(PRIMARY_AUTHORS)}})
    secondary_where = _build_where({"author": {"$in": list(SECONDARY_AUTHORS)}})
    # Books and other sources have empty author — query with no author filter
    books_where     = _build_where({})
    logging.info(f"[RAG] tier1 where: {primary_where}")
    logging.info(f"[RAG] tier2 where: {secondary_where}")
    logging.info(f"[RAG] tier3 (books/other) where: {books_where}")

    def _query_isolated(where, n):
        """Standalone query with its own collection — safe for concurrent use."""
        col = _get_collection()
        p = {
            "query_embeddings": [query_embedding],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            p["where"] = where
        try:
            return col.query(**p)
        except Exception as exc:
            logging.warning("[RAG] isolated vector query failed where=%s: %s", where, exc)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_primary   = ex.submit(_query_isolated, primary_where,   primary_k)
        f_secondary = ex.submit(_query_isolated, secondary_where, secondary_k)
        f_books     = ex.submit(_query_isolated, books_where,     books_k)
        primary   = f_primary.result()
        secondary = f_secondary.result()
        books     = f_books.result()

    n_primary   = _count(primary)
    n_secondary = _count(secondary)
    n_books     = _count(books)
    logging.info(f"[RAG] tier1={n_primary}, tier2={n_secondary}, tier3(books)={n_books}")

    # Guarantee at least 2 slots each for Marks and Li Lu so their perspective
    # always appears even when Buffett/Munger dominate on relevance.
    results = _merge_results(
        primary, secondary, books,
        top_k=top_k,
        guaranteed={"Howard Marks": 2, "Li Lu": 2},
    )
    results = _apply_reranker(search_query, results)
    _log_chunks(results, "Case B 3-tier merge (primary+secondary+books)")
    return results


# ── Streaming ─────────────────────────────────────────────────────────────────

def stream_query_knowledge_base(
    question: str,
    history: list = None,
    api_key: str = None,      # Deprecated; configuration is resolved by the gateway.
    top_k: int = TOP_K,
) -> Generator[str, None, None]:
    """
    SSE generator. Yields newline-delimited 'data: <json>\\n\\n' strings.
    Event types: searching | token | done | error
    """
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

    # 3. Stream answer tokens through the configured provider.
    gateway = get_generation_gateway()
    full_text = ""
    try:
        for text in gateway.stream(
            "knowledge_answer",
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        ):
            if text:
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
    api_key: str = None,      # Deprecated; configuration is resolved by the gateway.
    top_k: int = TOP_K,
) -> dict:
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
        response = get_generation_gateway().complete(
            "knowledge_answer",
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        raw_answer = response.text
        clean_answer, follow_ups = _parse_follow_ups(raw_answer)
        return {
            "answer": clean_answer,
            "sources": sources,
            "follow_ups": follow_ups,
            "search_params": search_params,
            "error": None,
        }
    except Exception as e:
        return {"answer": "", "sources": sources, "search_params": search_params, "error": f"API 调用失败: {e}"}


def retrieve_context(query: str, top_k: int = 8) -> tuple[str, list]:
    """Retrieve relevant chunks and return (context_string, sources_list).
    No LLM call — for use by endpoints that do their own generation (e.g. gym feedback)."""
    search_query = _translate_query(query)
    try:
        results = _retrieve(
            search_query, None, top_k,
            target_author=None,
        )
    except Exception:
        return "", []
    if not results["documents"] or not results["documents"][0]:
        return "", []
    return _format_context(results)
