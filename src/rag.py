"""
RAG query engine: ChromaDB retrieval + Claude API generation.
"""
import os
import re
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import anthropic

SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
DB_DIR   = ROOT_DIR / "database"

COLLECTION_NAME = "buffett_kb"
EMBED_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"
CLAUDE_MODEL    = "claude-haiku-4-5-20251001"
TOP_K           = 10

SYSTEM_PROMPT = """你是一个专业且严谨的"价值投资文献分析引擎"。

知识库来源：巴菲特致股东信（1977–2025，缺1978–1979年）、查理·芒格著述、Howard Marks备忘录、李录演讲与著作。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【零号准则：语言一致性】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **绝对强制**：用与用户提问完全相同的语言回答，包括所有标题、摘要、正文、追问。
- 若用户用英文提问，将所有检索到的中文内容翻译为英文，禁止中英混杂。
- CRITICAL: English question → English-only response. Translate ALL retrieved Chinese text.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式一：深度引用模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：问题涉及具体观点、原话、思想溯源。
规则：
- 每个关键事实或逻辑断言末尾必须紧跟来源标注，如 [来源1] 或 [来源1, 2]。
- 优先引用原文片段（用引号），注明作者、年份、文档类型。
- 若多位作者（巴菲特/芒格/Marks/李录）有相似观点，并列呈现，标注各自来源。
- 禁止在无来源支撑时进行推断或补全。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式二A：已知公司模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户问巴菲特/芒格/Marks/李录在文献中直接提及过的公司（如可口可乐、GEICO、比亚迪、苹果等）。
规则：
- 从知识库找大师对这家公司的原话评价，按以下结构组织答案：
  ① **公司基本面描述**：大师如何定义这家公司的商业模式与竞争地位。
  ② **大师评价原文**：直接引用原文片段，注明来源与年份。
  ③ **买入/持有/卖出逻辑**：文献中明确陈述的决策依据。
  ④ **时间演变**：若多年有提及，按时间线呈现观点变化。
- 用分年份列表或表格呈现演变脉络。
- 严格区分"文献有记载"与"文献未提及"，后者标注"知识库未收录此信息"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式二B：用户自研公司模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：用户提到知识库未直接覆盖的公司，或明确说"我想分析XX公司"。
规则：
- **不给结论**，引导用户用五步框架自己判断：
  **第一步：商业模式**——用一句话解释这家公司如何赚钱？
  **第二步：护城河来源**——品牌 / 网络效应 / 转换成本 / 成本优势 / 监管许可，各自是否成立？
  **第三步：管理层资本分配**——历史上管理层如何使用留存收益？有无回购、并购、分红记录？
  **第四步：当前市场情绪**——市场目前是贪婪还是恐惧？估值处于历史什么分位？
  **第五步：巴菲特优先检验点**——如果巴菲特看这家公司，他最先会检验哪一点？
- 每一步均援引知识库相关原则作参照，并注明来源（如"参照[来源X]巴菲特1986年对护城河的定义"）。
- 明确告知用户："以上框架来自知识库原则，具体数据与结论需用户自行研判。"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式三：角度转化模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：问题要求"如果巴菲特/芒格/Marks/李录来看这个问题，他会怎么想？"或要求对比不同投资人视角。
规则：
- 以"[人名]的视角"为小标题，分别阐述各人的思维框架与立场。
- 每个视角必须锚定知识库原文，不得凭空捏造观点。
- 若知识库中某人未直接论及该话题，写明"[人名]在现有文献中未直接论及此题"，但可援引其相关原则推演，并标注"推演自[来源X]"。
- 最后提供"视角差异小结"，指出各人最核心的分歧点。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模式四：诚实边界模式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
触发：检索内容不足、问题超出知识库范围、或问题涉及知识库成文后发生的事件。
规则：
- 直接、明确声明知识库的局限，例如："现有文献未覆盖此话题"、"1978–1979年股东信缺失，该时期信息不完整"。
- 禁止用模糊语言掩盖信息缺失（如"可能"、"大概"）。
- 可提示用户缩小问题范围或换一个知识库有记载的角度。
- 若问题涉及2025年后事件，明确告知："知识库收录截至2025年，此后信息不在范围内"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【通用排版规范】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **执行摘要**：开头一句加粗核心结论，如 **核心结论：……[来源1]**
- **主题分组**：2–3个`###`标题，禁止所有要点平铺在一个大列表。
- **主次列表**：一级列表加粗核心短语；二级列表缩进，列具体年份/数据/案例。
- **禁止文字墙**：连续段落不超过3行，多用换行留白。
- **客观叙述**：用"根据[来源]指出……"、"资料显示……"，禁用"我认为"、"建议"。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【追问规范】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 回答末尾必须输出完整的 <follow_ups>…</follow_ups> 标签（开闭标签缺一不可）。
- 提供3个追问，语言与用户提问一致。
- 每个追问不超过15个字（中文）或15个英文单词。
- 格式示例：
<follow_ups>
1. 护城河如何量化评估？
2. 芒格与巴菲特的分歧？
3. 李录如何看中国投资？
</follow_ups>"""


def _get_collection():
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def _format_context(results: dict) -> tuple[str, list[dict]]:
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

        # Extract extended context from original file if possible
        full_context = ""
        try:
            source_file = meta.get("source_file")
            if source_file:
                md_path = ROOT_DIR / "data" / "clean_mds" / source_file
                if md_path.exists():
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Strip frontmatter
                        if content.startswith("---\n"):
                            parts = content.split("---\n", 2)
                            if len(parts) >= 3:
                                content = parts[2].strip()
                        
                        idx = content.find(doc)
                        if idx != -1:
                            start = max(0, idx - 8000)
                            end = min(len(content), idx + len(doc) + 8000)
                            # snap to nearest line breaks
                            start_snap = content.rfind("\n", 0, start)
                            end_snap = content.find("\n", end)
                            start = start_snap if start_snap != -1 else start
                            end = end_snap if end_snap != -1 else end
                            
                            full_context = content[start:end]
                            if start > 0:
                                full_context = "...\n\n" + full_context.lstrip()
                            if end < len(content):
                                full_context = full_context.rstrip() + "\n\n..."
                        else:
                            full_context = content[:16000]
        except Exception:
            pass

        source = {
            "label":    meta["source_label"],
            "year":     meta.get("year", 0),
            "doc_type": meta.get("doc_type", ""),
            "section":  meta.get("section", ""),
            "text":     doc,
            "full_context": full_context,
            "relevance": relevance,
        }
        if meta.get("cnbc_url"):
            source["url"] = meta["cnbc_url"]
        sources.append(source)

    context = "\n\n---\n\n".join(context_parts)
    return context, sources


def query_knowledge_base(
    question: str,
    history: list = None,
    api_key: Optional[str] = None,
    top_k: int = TOP_K,
) -> dict:
    """
    Query the knowledge base using Claude.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {"answer": "", "sources": [], "error": "未设置 ANTHROPIC_API_KEY"}

    client = anthropic.Anthropic(api_key=key)

    # 1. Expand query using history for better retrieval context
    search_query = question
    where_clause = None
    try:
        import json

        history_context = ""
        if history and len(history) > 0:
            history_context = "Recent conversation context:\n"
            for msg in history[-3:]:  # Only use last 3 turns to prevent dilution
                role = "User" if msg["role"] == "user" else "Assistant"
                history_context += f"{role}: {msg['content'][:200]}\n"

        prompt = f"""{history_context}

Task: Analyze user query for a Buffett/Munger RAG system.
1. search_query: 2-3 English keywords.
2. year: Extract year if mentioned, else null.
3. doc_type: "shareholder_letter", "meeting_transcript", or "munger_wisdom" if mentioned, else null.

User Question: {question}

Return ONLY JSON:
{{
  "search_query": "keywords",
  "year": 2000 or null,
  "doc_type": "type" or null
}}
"""
        trans_res = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        json_match = re.search(r'\{.*\}', trans_res.content[0].text.strip(), re.DOTALL)

        search_params = {"query": search_query, "year": None, "doc_type": None}
        if json_match:
            parsed = json.loads(json_match.group(0))
            search_query = parsed.get("search_query", question)
            search_params["query"] = search_query

            where = {}
            if parsed.get("year"):
                where["year"] = int(parsed.get("year"))
                search_params["year"] = where["year"]
            if parsed.get("doc_type"):
                where["doc_type"] = parsed.get("doc_type")
                search_params["doc_type"] = where["doc_type"]

            if where:
                if len(where) == 1:
                    where_clause = where
                else:
                    where_clause = {"$and": [{k: v} for k, v in where.items()]}
    except Exception as e:
        print(f"Translation/JSON extraction failed: {e}")
        search_params = {"query": question, "year": None, "doc_type": None}

    # 2. Retrieve from ChromaDB
    try:
        collection = _get_collection()
    except Exception as e:
        return {"answer": "", "sources": [], "error": f"数据库初始化失败\n({e})"}

    try:
        query_params = {
            "query_texts": [search_query],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"]
        }
        if where_clause:
            query_params["where"] = where_clause
            
        results = collection.query(**query_params)
        
        # Fallback if empty due to strict filtering
        if (not results["documents"] or not results["documents"][0]) and where_clause:
            del query_params["where"]
            results = collection.query(**query_params)
            
    except Exception as e:
        return {"answer": "", "sources": [], "error": f"检索失败: {e}"}

    if not results["documents"] or not results["documents"][0]:
        return {"answer": "知识库为空，请先运行 ingest.py", "sources": [], "search_params": search_params, "error": None}

    context, sources = _format_context(results)

    # 3. Format history for chat session (Anthropic format)
    chat_history = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            chat_history.append({"role": role, "content": msg["content"]})

    # 4. Final user message with context
    user_msg = (
        "【当前检索到的知识库内容】\n"
        f"{context}\n\n"
        "---\n\n"
        f"【当前用户提问 / Current User Question】：{question}\n\n"
        "CRITICAL INSTRUCTION:\n"
        "1. Identify the language of the user's question.\n"
        "2. You MUST formulate your ENTIRE response (including the <follow_ups> section) in THAT EXACT LANGUAGE.\n"
        "3. If the question is in English, you must TRANSLATE all facts from the retrieved Chinese context into English. DO NOT output any Chinese characters.\n"
        "4. Strict layout: Executive Summary -> Thematic Grouping -> Bullet Points -> <follow_ups>."
    )

    try:
        messages = chat_history + [{"role": "user", "content": user_msg}]
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        raw_answer = response.content[0].text

        # Parse follow_ups
        follow_ups = []
        match = re.search(r"<follow_ups>(.*?)</follow_ups>", raw_answer, re.DOTALL)
        if match:
            follow_ups_text = match.group(1).strip()
            raw_answer = raw_answer.replace(match.group(0), "").strip()

            for line in follow_ups_text.split("\n"):
                line = line.strip()
                clean_line = re.sub(r"^(\d+\.|\-|•)\s*", "", line)
                if clean_line:
                    follow_ups.append(clean_line)

        return {
            "answer": raw_answer,
            "sources": sources,
            "follow_ups": follow_ups,
            "search_params": search_params,
            "error": None
        }
    except Exception as e:
        return {"answer": "", "sources": sources, "search_params": search_params, "error": f"Claude API 调用失败: {e}"}
