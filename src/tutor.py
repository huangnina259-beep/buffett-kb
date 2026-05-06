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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【本章详细教案】（仅当前章节适用,推进后会换）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{current_lesson}

如果这是本章第一轮（学生消息为空或只是问候）：
- 直接用上面的"开场钩子"打开对话,不要寒暄
- 不要一次性介绍整章内容,只抛这一个钩子
- 钩子之后等学生回答,再展开

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


# ── Chapter labels ───────────────────────────────────────────────────────────

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

# ── Per-chapter lesson plans ─────────────────────────────────────────────────
# Each chapter has:
#   hook:           opening question the AI uses verbatim (or near-verbatim) on first turn
#   core:           the one idea student must internalize to advance
#   misconceptions: common wrong beliefs to watch for and surface via questioning
#   kb_query:       English query for KB retrieval on opening turn
#   anchor_authors: which authors' KB excerpts are most relevant (guides retrieval/citation)
#   advance:        concrete signals that student has internalized the core

CHAPTER_LESSONS = {
    "ch1": {
        "hook": "你买过股票吗?如果买过,在你按下'买入'那一刻,脑子里想的是这家公司本身,还是想的是'它会不会涨'?",
        "core": "股票不是一张可以涨跌的纸,是公司的一小块所有权",
        "misconceptions": [
            "把股票当数字游戏(看 K 线决定买卖)",
            "短线博弈思维(明天涨了就卖)",
            "只关心价格,不关心公司",
        ],
        "kb_query": "Graham intelligent investor stock business ownership Buffett 10 years hold company",
        "anchor_authors": ["Benjamin Graham", "Warren Buffett"],
        "advance": [
            "学生明确说出'股票=公司的一部分/所有权'(用自己的话)",
            "并能解释为什么这个视角不同于多数人(比如:你会关心公司本身,不只是股价)",
        ],
    },
    "ch2": {
        "hook": "想象你的邻居说他家房子值 500 万。第二天他突然来跟你说'我急用钱,300 万就卖给你'。你会买吗?为什么——你怎么知道他的房子'真正值多少'?",
        "core": "价格是市场每天报的数字,价值是公司未来现金流的现值。两者经常不一样,这正是机会的来源。",
        "misconceptions": [
            "股价跌 = 公司变差(其实可能是别人恐慌)",
            "股价涨 = 公司变好(其实可能是别人贪婪)",
            "价格 = 价值(把市场报价当真理)",
        ],
        "kb_query": "Graham intrinsic value price weighing voting machine Buffett value vs price",
        "anchor_authors": ["Benjamin Graham", "Warren Buffett"],
        "advance": [
            "学生能区分'价格变化'和'价值变化',并举出一个例子(如:好公司股价腰斩但生意没变)",
            "理解'价格 < 价值'是机会,不是危险",
        ],
    },
    "ch3": {
        "hook": "假设你和一个情绪极不稳定的人合伙开店。这个人每天来跟你说:'今天我心情好,我用 500 万买你的份额!'或者'今天我看跌,我把我的份额 100 万卖给你!'——你会怎么对待这个合伙人?",
        "core": "市场是个情绪化的合伙人(Mr. Market),他每天给你报价。他是仆人,不是老师——你可以利用他,但不该被他左右",
        "misconceptions": [
            "市场总是对的(其实经常情绪化)",
            "跌的时候应该跟着卖(其实可能是机会)",
            "涨的时候应该追(其实可能是泡沫)",
        ],
        "kb_query": "Graham Mr Market manic depressive Buffett market serve instruct emotional",
        "anchor_authors": ["Benjamin Graham", "Warren Buffett"],
        "advance": [
            "学生能复述'市场先生是仆人,不是老师'的精神(用自己的话)",
            "能描述什么时候应该理他(便宜时买、贵时卖)、什么时候不该理他(随波逐流)",
        ],
    },
    "ch4": {
        "hook": "我给你两个选择:A) 现在直接拿 100 万。B) 我给你 1 分钱,但每天翻倍,持续 30 天。你选哪个?——先不要算,先猜。",
        "core": "复利不是线性,是指数。高 ROIC × 长时间 = 数学奇迹。差距大到反直觉",
        "misconceptions": [
            "7% 和 15% 年化看起来差不多",
            "复利是个慢慢的过程(其实越后面越爆炸)",
            "年回报率才重要(其实'持续 + 时间'才是核心)",
        ],
        "kb_query": "Buffett compounding 99% wealth after age 50 long term ROIC Munger don't interrupt compounding",
        "anchor_authors": ["Warren Buffett", "Charlie Munger"],
        "advance": [
            "学生有'原来差距这么大'的反应(数字震撼到他)",
            "能说出'找高 ROIC 公司 + 长期持有'的策略含义",
        ],
    },
    "ch5": {
        "hook": "如果有人神秘兮兮告诉你:'我朋友在内部听说,下个月某家生物科技公司的新药要批准,股价会涨 10 倍。' 你会买吗?为什么会或为什么不?",
        "core": "知道自己不知道什么,比知道很多更重要。能力圈不需要大,但必须知道边界",
        "misconceptions": [
            "懂得越多越好(其实知道边界更重要)",
            "错过机会就是损失(其实跨出能力圈才是真损失)",
            "'机会'值得赌一把(Munger:错就错在'just this once')",
        ],
        "kb_query": "Buffett circle of competence Munger inversion know what you don't know technology stocks",
        "anchor_authors": ["Warren Buffett", "Charlie Munger"],
        "advance": [
            "学生能说出'我应该只投我能理解的公司'",
            "能给出一个具体测试:什么算'理解'(如:能用一句话讲清这家公司怎么赚钱)",
        ],
    },
    "ch6": {
        "hook": "如果你要造一座桥,设计要承重 10 吨车辆经过——你会按 10 吨设计,还是按 30 吨设计?为什么要多加这 20 吨的'冗余'?",
        "core": "安全边际不只是'打折买'的数学,是承认'我会犯错'的心理空间。给不确定性留余地",
        "misconceptions": [
            "安全边际 = 便宜(P/E 低)",
            "有安全边际就一定不亏",
            "估值精确就够了(其实你的估值本身可能错)",
        ],
        "kb_query": "Graham margin of safety central concept Buffett never lose money rule Howard Marks pricing uncertainty",
        "anchor_authors": ["Benjamin Graham", "Warren Buffett", "Howard Marks"],
        "advance": [
            "学生能说出'安全边际不只是便宜,是为我自己的判断错误留余地'",
            "能反思自己以前可能犯过什么错(过度自信、估值过乐观)",
        ],
    },
    "ch7": {
        "hook": "过去 30 年,标普 500 指数年化收益约 10%。但同期个人投资者的实际收益,平均只有 3-4%。差的那 6-7% 去哪了?",
        "core": "复利发生需要的耐心,大多数人付不起。市场最终奖励能等的人,而'能等'是练出来的稀缺品质",
        "misconceptions": [
            "长期持有很容易",
            "我能扛住 50% 回撤(没真经历过的人都这么说)",
            "耐心是性格(其实是练出来的)",
        ],
        "kb_query": "Buffett patience compounding stock market transfer impatient Munger 50% drawdown Howard Marks contrarian",
        "anchor_authors": ["Warren Buffett", "Charlie Munger", "Howard Marks"],
        "advance": [
            "学生能说出'为什么大多数人做不到长期持有'",
            "能诚实说出自己最可能在什么情况下放弃(熊市/亏损/朋友赚钱压力)",
        ],
    },
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


def _build_lesson(state: dict) -> str:
    """Build the per-chapter lesson plan injected into the system prompt."""
    chapter = state.get("currentChapter") or state.get("currentCycle", "ch1")
    lesson = CHAPTER_LESSONS.get(chapter)
    if not lesson:
        return "(本章教案未配置,使用通用对话方法)"

    misconceptions = "\n".join(f"  - {m}" for m in lesson.get("misconceptions", []))
    advance = "\n".join(f"  - {a}" for a in lesson.get("advance", []))
    authors = ", ".join(lesson.get("anchor_authors", []))

    return f"""开场钩子(若是本章第一轮,直接抛出这个问题,不寒暄):
  「{lesson['hook']}」

核心概念(学生必须内化的那一个想法):
  {lesson['core']}

学生常见误区(用反问帮他自己发现):
{misconceptions}

KB 锚点作者(优先在恰当时机引用这些人的原文,使用 [来源N] 格式):
  {authors}

推进信号(满足任一即可在本轮回复末尾添加 <advance_to> 标签):
{advance}"""


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

    # On opening turn (empty message), use the chapter's curated KB query;
    # otherwise use the student's actual message for relevance to the dialog.
    chapter_id = state.get("currentChapter") or state.get("currentCycle", "ch1")
    chapter_lesson = CHAPTER_LESSONS.get(chapter_id, {})
    retrieval_query = message.strip() if message and message.strip() else chapter_lesson.get("kb_query", "value investing")

    context, sources = _retrieve_for_tutor(retrieval_query)

    # 2. Build system prompt with current position + per-chapter lesson plan
    position = _build_position(state)
    lesson = _build_lesson(state)
    system = (
        TUTOR_SYSTEM_PROMPT
        .replace("{current_position}", position)
        .replace("{current_lesson}", lesson)
    )

    # 3. Build messages
    msgs = []
    if history:
        for h in history:
            role = h.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            msgs.append({"role": role, "content": h["content"]})

    is_opening = not (message and message.strip())
    if is_opening:
        # Opening turn: send a structured trigger so the AI knows to use the chapter's hook
        student_block = f"(本章第一轮——请直接用【本章详细教案】里的开场钩子打开对话,不要寒暄)"
    else:
        student_block = f"【学生回答】:{message}"

    if context:
        user_content = f"【知识库参考内容】\n{context}\n\n---\n\n{student_block}"
    else:
        user_content = student_block

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
