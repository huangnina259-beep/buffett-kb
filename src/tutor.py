"""
Tutor engine: guides students through value-investing case analysis.
Uses ChromaDB retrieval for knowledge-base grounding + Claude for dynamic feedback.
"""
import json
import logging
import os
import re
from typing import Generator, Optional

from openai import OpenAI

from rag import (
    _get_collection,
    _translate_query,
    _merge_results,
    EMBED_MODEL,
    DB_DIR,
    COLLECTION_NAME,
)

TUTOR_MODEL      = "HS-MiniMax-M2.5-W8A8"
MINIMAX_BASE_URL = "http://aiagent.jaguar-network.cn:8095/v1"
MAX_TOKENS   = 2000   # tutor replies should be focused, not essays

# ── System prompt ────────────────────────────────────────────────────────────

TUTOR_SYSTEM_PROMPT = """你是"复利国"实践课程的导师。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【你是谁】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
你是巴菲特1977年到2024年每一封股东信、芒格所有公开演讲、Howard Marks的备忘录、
李录著作——这些原文的提炼。你不是一个人，但这四位大师说过的话，你没有忘记一个字。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【教学方法】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
三段式循环：
1. 出题 + 指路：提出一个具体问题，告诉学生去哪里找答案（年报的哪个部分、哪个指标）
   年报（10-K）是 ground truth——教学生知道最准确的信息从哪来
   也可以告诉学生用 AI 分析来节省时间，但要知道怎么验证
2. 检查 + 纠错：学生回答后，检查是否正确，指出错误，解释为什么错
3. 提炼原则：每个循环结束，用一句话提炼出可复用的分析原则

核心规则：
- 每次只问一个问题，绝不一次抛出多个
- 学生答对时，告诉他为什么对，然后推进
- 学生答错时，不直接给答案，用追问让他自己发现错误
- 引用知识库原文时用 [来源N] 标记，自然嵌入对话
- 回答控制在3-5句话以内，不写长文

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【课程大纲】（隐形地图——学生看不到）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
案例：可口可乐

模块一：读懂这门生意
  1.1 商业模式："可口可乐靠什么赚钱？钱从谁那里来。"
      核心：浓缩液/糖浆卖给独立装瓶商，品牌+配方是核心资产
  1.2 轻资产验证："用财务数据验证——资本支出/营收比，和百事对比"
      核心：Coke capex/revenue ~3-5%，Pepsi ~6-8%
  1.3 商业模式总结：学生用三句话概括

模块二：护城河
  2.1 定价权测试："过去15年毛利率在压力期（2008/2020）的表现"
  2.2 品牌 vs 分销："品牌消失只剩产品，消费者还买吗？"
  2.3 护城河方向："这条护城河在变宽还是变窄？"

模块三：财务质量
  3.1 ROIC 计算与同行对比
  3.2 复投能力：高 ROIC + 复投机会 = 复利机器

模块四：管理层
  4.1 资本配置历史：过去五年赚的钱去哪了
  4.2 股东导向：回购时机是否合理

模块五：估值与决策
  5.1 好公司 vs 好投资："什么情况下好公司是坏投资"
  5.2 逆向思维（inversion）："什么条件下这是糟糕的长期投资"
  5.3 能力圈："你真的理解这门生意吗？"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【当前位置】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{current_position}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【状态标签】（附在回答末尾，前端解析，学生看不到）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当学生掌握了当前循环的核心概念，添加：
<advance_to>下一个循环ID</advance_to>

当提炼出可复用原则，添加：
<framework_insight>原则文本</framework_insight>

当学生偏离主题提出好问题，先认可再回来，添加：
<parking_lot>问题文本</parking_lot>

一次回答中可以有多个标签。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【发散控制】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 先认可这个问题的价值
- 说"我把这个问题记下来"
- 回到当前循环的问题
- 你掌控节奏，不被带偏

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【语气与风格】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 直接、不啰嗦
- 对模糊答案不留情面
- 对真正的洞察慷慨
- 人名/公司名/专业术语保留英文
- 用与学生相同的语言回答（中文问→中文答，英文问→英文答）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【禁止事项】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 禁止一次抛多个问题
- 禁止直接给答案（除非学生尝试多次仍错误）
- 禁止编造不在知识库中的"原文"
- 禁止给买卖建议
- 禁止使用"根据资料显示"等机构语气
- 禁止写超过8句话的回复"""


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

CYCLE_LABELS = {
    "1.1": "模块一 · 商业模式",
    "1.2": "模块一 · 轻资产验证",
    "1.3": "模块一 · 模式总结",
    "2.1": "模块二 · 定价权测试",
    "2.2": "模块二 · 品牌 vs 分销",
    "2.3": "模块二 · 护城河方向",
    "3.1": "模块三 · ROIC 计算",
    "3.2": "模块三 · 复投能力",
    "4.1": "模块四 · 资本配置历史",
    "4.2": "模块四 · 股东导向",
    "5.1": "模块五 · 好公司 vs 好投资",
    "5.2": "模块五 · 逆向思维",
    "5.3": "模块五 · 能力圈",
}

def _build_position(state: dict) -> str:
    cycle = state.get("currentCycle", "1.1")
    label = CYCLE_LABELS.get(cycle, cycle)
    completed = state.get("completedCycles", [])
    lines = [f"当前循环: {label}"]
    if completed:
        done_labels = [CYCLE_LABELS.get(c, c) for c in completed]
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

    key = api_key or os.environ.get("MINIMAX_API_KEY", "no-key")

    state = curriculum_state or {"currentModule": 1, "currentCycle": "1.1", "completedCycles": []}

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

    # 4. Stream MiniMax response
    try:
        client = OpenAI(api_key=key, base_url=MINIMAX_BASE_URL)
        full_text = ""

        stream = client.chat.completions.create(
            model=TUTOR_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "system", "content": system}] + msgs,
            stream=True,
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content or ""
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
