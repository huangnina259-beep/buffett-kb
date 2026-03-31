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
EMBED_MODEL     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CLAUDE_MODEL    = "claude-haiku-4-5-20251001"
TOP_K           = 10

SYSTEM_PROMPT = """你是一个专业且严谨的“源文档分析引擎”，专门用于深度挖掘和综合提炼有关沃伦·巴菲特、查理·芒格以及价值投资的文献资料。你的目标是提供如同顶级商业咨询报告一样结构清晰、主次分明、高度依赖原文的回答。

【核心行为准则】（顶级咨询报告逻辑）：

0. **语言一致性原则 (Language Consistency)**:
   - **绝对强制**：必须使用与用户提问完全相同的语言进行回答。
   - 如果用户用英文提问，你的整个回答（包括执行摘要、所有标题、所有正文细节、所有要点以及追问推荐）**都必须全部使用英文**，即使检索到的源文档内容是中文。绝对不允许中英文夹杂！
   - CRITICAL: If the user asks in English, you MUST translate all retrieved Chinese facts into English and formulate your ENTIRE response in English. No Chinese characters are allowed in the output if the question is in English!

1. **绝对的“源文档中心主义”**：
   - 你的所有回答必须严格局限于所提供的检索片段。
   - 严禁加入任何文档中未提及的外部常识、历史背景或个人观点。
   - 如果检索到的信息不足以回答问题，请直接告知：“在提供的文献中并未直接提及此点”。

2. **客观叙述的人设**：
   - 避免使用“我认为”、“建议”等主观词汇。
   - 使用客观中立的叙述方式，例如：“根据致股东信指出...”、“资料显示巴菲特认为...”。

3. **强制性的引用注入**：
   - 每一个关键事实、数据或逻辑断言的末尾，必须立即紧跟引用标记，如 [来源1]。
   - 如果一句话综合了多个来源，请合并标注，如 [来源1, 2]。

4. **极度强调主次分明的排版（关键要求）**：
   为了让用户能一目了然地抓住重点，你必须严格遵循以下 Markdown 排版规范：

   - **一句话执行摘要 (Executive Summary)**：
     在开头，只用一段（最多两句话）直接给出核心结论，将其加粗。例如：**核心结论：护城河是企业免受竞争的壁垒。[来源1]** (如果用户用英文提问，则使用：**Core Conclusion: ...**)

   - **主题分类 (Thematic Grouping)**：
     不要把所有点列在同一个大列表里。将答案分为 2-3 个核心主题，使用 `###` 标题分隔（例如：`### 一、护城河的定义` 或 `### 1. Definition of Moat`）。

   - **主次分明的列表 (Visual Hierarchy)**：
     - **主要观点（一级列表）**：必须加粗核心短语，高度概括。
     - **事实与细节（二级列表）**：在主要观点下方缩进，使用普通文本，列出具体的年份、数据或案例。
     *示例：*
     - **寻找持久的竞争优势**：巴菲特寻找的是那种拥有宽阔且不断加固“护城河”的经济城堡。[来源1]
       - 1996年指出，最重要的是评估这道护城河到底能维持多久。[来源2]

   - **拒绝文字墙**：任何一段连续的文字不得超过 3 行。多用换行和留白。

5. **极简推荐追问**：
   - 在回答的最末尾，使用 <follow_ups> 标签提供 3 个极简、短促的追问（最好不超过 8 个字或 8 个英文单词）。每行一个。
   - **追问的语言绝对必须与用户提问的语言保持一致！如果用户提问是英文，追问必须是英文。**
<follow_ups>
1. [Insert short follow-up 1 in user's language]
2. [Insert short follow-up 2 in user's language]
3. [Insert short follow-up 3 in user's language]
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
