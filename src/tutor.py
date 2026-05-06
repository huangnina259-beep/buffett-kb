"""
Tutor engine: guides students through value-investing case analysis.
Uses ChromaDB retrieval for knowledge-base grounding + Claude for dynamic feedback.
"""
import json
import logging
import os
import re
from typing import Generator, Optional

from anthropic import Anthropic

from rag import (
    _get_collection,
    _translate_query,
    _merge_results,
    EMBED_MODEL,
    DB_DIR,
    COLLECTION_NAME,
)

TUTOR_MODEL  = os.environ.get("TUTOR_MODEL", "claude-sonnet-4-6")
MAX_TOKENS   = 2000   # tutor replies should be focused, not essays

# ── System prompt ────────────────────────────────────────────────────────────

TUTOR_SYSTEM_PROMPT = """你是"复利国"价值投资理论课的导师。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【你是谁】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
你是 Benjamin Graham 经典著作、Warren Buffett 1977-2024 所有股东信、
Charlie Munger 公开演讲、Howard Marks 备忘录、Li Lu 著作——这些原文的提炼。
你不是一个人，但这五位大师说过的话，你没有忘记一个字。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【教学方法 · 苏格拉底式对话】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
本课程是 7 个理论章节的对话式学习。每章一个核心思想，5-8 轮对话学完。

每一轮的节奏：
1. 提出一个引发思考的问题（场景化、有钩子，避免抽象提问）
2. 学生回答后，不评分，用反问引导他自己发现盲点
3. 在关键时刻引用 Buffett/Munger/Graham/Marks/李录 原话锚定（[来源N]）
4. 章节末尾让学生用**自己的话**总结核心概念——这是"学会了"的检验

章节推进的判断标准：
- 学生用**自己的语言**（不照抄你的话）清晰表达了本章核心
- 同时表现出能把这个概念**应用**到一个具体场景
- 满足以上两点 → 推进到下一章

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【7 个理论章节】（隐形地图——学生看不到细节）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ch1 · 股票 = 公司的一部分（Graham 第一原则）
   核心：股票不是一张可以涨跌的纸,是公司的一小块所有权
   关键 KB 来源：Graham《聪明的投资者》、Buffett 早期股东信
   推进信号：学生能说出"我买股票其实是买公司的一部分"并能解释为什么这个视角不同

ch2 · 价格 ≠ 价值（内在价值）
   核心：价格是市场每天的报价,价值是公司未来现金流折现
   推进信号：学生区分得出"股价跌不代表公司变差"

ch3 · 市场先生（Mr. Market）
   核心：市场是情绪化的合伙人,他给你报价,你可以接受或不理
   推进信号：学生能说出"市场先生是仆人,不是老师"

ch4 · 复利的力量
   核心：7% vs 15% 在 30 年后是天壤之别——高 ROIC × 长时间 = 数学奇迹
   推进信号：学生有"原来这个差距这么大"的反应,并知道找高 ROIC 公司

ch5 · 能力圈（Circle of Competence）
   核心：知道自己不知道什么,比知道很多更重要
   推进信号：学生能说出"我应该只投资我能理解的"并举例什么是"理解"

ch6 · 安全边际
   核心：不只是"打折买"的数学,是承认自己会犯错的心理空间
   推进信号：学生理解"安全边际 ≠ 便宜",而是"为不确定性留余地"

ch7 · 长期主义的真实代价
   核心：复利发生需要的耐心,大多数人付不起;市场最终奖励能等的人
   推进信号：学生能说出"为什么大部分人做不到长期持有"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【当前位置】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{current_position}

如果这是新会话第一轮（学生消息为空或问候）：
- 用本章对应的开场问题打开对话
- 不要一次性介绍整章,只问一个具体钩子问题

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【状态标签】（前端解析,学生看不到）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
学生用自己的话清晰表达本章核心 + 能应用 → <advance_to>下一章ID</advance_to>
（章节顺序: ch1→ch2→ch3→ch4→ch5→ch6→ch7→done）

提炼出可复用洞见 → <framework_insight>洞见文本</framework_insight>

学生偏离主题提出好问题（先认可再拉回） → <parking_lot>问题文本</parking_lot>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【回答规则】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 一次只问一个问题,绝不一次抛多个
- 回答 1-4 句话,不写长文
- 学生答错时反问,**不直接给答案**(除非反问 2 次都还偏)
- 只在关键"啊哈"时刻引用 KB 原文,不堆砌
- 中文问→中文答,英文问→英文答
- 人名/公司名/专业术语保留英文(Buffett, ROIC, P/E)
- 直接、不啰嗦
- 对模糊答案不留情面,对真正的洞察慷慨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【禁止】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 一次抛多个问题
- 直接讲课/列要点
- 编造不在 KB 的"原文"
- 给买卖建议或推荐公司
- 用"根据资料显示"这种机构语气
- 写超过 5 句话的回复"""


# ── Retrieval helper ─────────────────────────────────────────────────────────

def _retrieve_for_tutor(question: str, n_results: int = 6) -> tuple:
    """Retrieve relevant chunks from the knowledge base for tutor grounding."""
    search_query = _translate_query(question)
    collection = _get_collection()
    try:
        results = collection.query(
            query_texts=[search_query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return "", []

    docs  = results["documents"][0] if results["documents"] and results["documents"][0] else []
    metas = results["metadatas"][0] if results["metadatas"] and results["metadatas"][0] else []

    context_parts = []
    sources = []
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        author = meta.get("author", "")
        year   = meta.get("year", "")
        label  = meta.get("source_label", "")
        header = f"[来源{i}] {label} ({year}) | {author}"
        context_parts.append(f"{header}\n{doc}")
        sources.append({"label": label, "author": author, "year": year})

    return "\n\n---\n\n".join(context_parts), sources


# ── Meta-tag parsing ─────────────────────────────────────────────────────────

def _parse_tutor_meta(text: str) -> dict:
    """Extract <advance_to>, <framework_insight>, <parking_lot> tags."""
    meta = {}

    m = re.search(r"<advance_to>(.*?)</advance_to>", text, re.DOTALL)
    if m:
        meta["advance_to"] = m.group(1).strip()

    m = re.search(r"<framework_insight>(.*?)</framework_insight>", text, re.DOTALL)
    if m:
        meta["framework_insight"] = m.group(1).strip()

    m = re.search(r"<parking_lot>(.*?)</parking_lot>", text, re.DOTALL)
    if m:
        meta["parking_lot"] = m.group(1).strip()

    return meta


def _strip_meta_tags(text: str) -> str:
    """Remove meta tags from the visible response."""
    text = re.sub(r"<advance_to>.*?</advance_to>", "", text, flags=re.DOTALL)
    text = re.sub(r"<framework_insight>.*?</framework_insight>", "", text, flags=re.DOTALL)
    text = re.sub(r"<parking_lot>.*?</parking_lot>", "", text, flags=re.DOTALL)
    return text.strip()


# ── Build position string ────────────────────────────────────────────────────

CHAPTER_LABELS = {
    "ch1": "第 1 章 · 股票 = 公司的一部分",
    "ch2": "第 2 章 · 价格 ≠ 价值",
    "ch3": "第 3 章 · 市场先生",
    "ch4": "第 4 章 · 复利的力量",
    "ch5": "第 5 章 · 能力圈",
    "ch6": "第 6 章 · 安全边际",
    "ch7": "第 7 章 · 长期主义的真实代价",
    "done": "课程完成",
}

def _build_position(state: dict) -> str:
    chapter = state.get("currentChapter") or state.get("currentCycle", "ch1")
    label = CHAPTER_LABELS.get(chapter, chapter)
    completed = state.get("completedChapters") or state.get("completedCycles", [])
    lines = [f"当前章节: {label}"]
    if completed:
        done_labels = [CHAPTER_LABELS.get(c, c) for c in completed]
        lines.append(f"已完成: {', '.join(done_labels)}")
    return "\n".join(lines)


# ── Streaming tutor response ─────────────────────────────────────────────────

def stream_tutor_response(
    message: str,
    history: list = None,
    curriculum_state: dict = None,
    api_key: str = None,
) -> Generator[str, None, None]:
    """SSE generator for tutor responses. Same event format as RAG chat."""

    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY 未设置'})}\n\n"
        return

    state = curriculum_state or {"currentChapter": "ch1", "completedChapters": []}

    # 1. Retrieve context from knowledge base
    yield f"data: {json.dumps({'type': 'searching'})}\n\n"

    context, sources = _retrieve_for_tutor(message)

    # 2. Build system prompt with current position
    position = _build_position(state)
    system = TUTOR_SYSTEM_PROMPT.replace("{current_position}", position)

    # 3. Build messages
    msgs = []
    if history:
        for h in history:
            role = h.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            msgs.append({"role": role, "content": h["content"]})

    user_content = message
    if context:
        user_content = (
            f"【知识库参考内容】\n{context}\n\n---\n\n"
            f"【学生回答】：{message}"
        )

    msgs.append({"role": "user", "content": user_content})

    # 4. Stream via Anthropic
    try:
        client = Anthropic(api_key=key)
        full_text = ""

        with client.messages.stream(
            model=TUTOR_MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=msgs,
        ) as stream:
            for text in stream.text_stream:
                if text:
                    full_text += text
                    # Don't stream meta tags to the user
                    if not re.search(r"<(advance_to|framework_insight|parking_lot)>", text):
                        yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"

        # 5. Parse meta and emit done event
        meta = _parse_tutor_meta(full_text)
        clean_text = _strip_meta_tags(full_text)

        done_evt = {
            "type": "done",
            "sources": sources,
            "final_answer": clean_text,
        }
        done_evt.update(meta)

        yield f"data: {json.dumps(done_evt)}\n\n"

    except Exception as e:
        logging.error(f"[Tutor] API error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
