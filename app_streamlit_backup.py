"""
Buffett Knowledge Base — NotebookLM UI Replica (Strict Precision)
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent / "src"))
from rag import query_knowledge_base

st.set_page_config(
    page_title="Buffett KB",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">

<style>
/* ── global ── */
html, body {
    height: 100% !important;
    overflow: hidden !important;
}
html, body, [class*="css"] { 
    font-family: 'Roboto', 'Google Sans', -apple-system, sans-serif;
    color: #202124;
    background-color: #f9f9f9;
}
#MainMenu, footer, header { visibility: hidden !important; display: none !important; }
.stApp { 
    background-color: #f9f9f9;
    overflow: hidden; /* Stop main page from scrolling */
}

/* 去除 Streamlit 默认的顶部 padding */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 0rem !important;
    max-width: 1400px;
    height: 100vh;
}

/* ── Columns independent scrolling ── */
[data-testid="stColumn"] {
    height: calc(100vh - 100px);
    overflow-y: auto;
    padding-bottom: 20px;
}
/* Ensure the vertical block inside the column takes full height so sticky works */
[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
    min-height: 100%;
    display: flex;
    flex-direction: column;
}
/* Push the chat input to the bottom of the flex container if needed, but sticky should work now */
div[data-testid="stChatInput"] {
    position: sticky !important;
    bottom: 0px !important;
    z-index: 999 !important;
    border-radius: 24px !important;
    border: 1px solid #e0e0e0 !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03) !important;
    background-color: white !important;
    padding: 4px 8px !important;
    margin-top: auto; /* Push to bottom of flex container */
    margin-bottom: 20px !important;
}
/* Streamlit 原生 Chat Message 定制 */
[data-testid="stChatMessage"] {
    background-color: transparent;
    border-radius: 0;
    padding: 0;
    box-shadow: none;
    margin-bottom: 32px;
    font-size: 15px;
    line-height: 1.65;
    color: #202124;
    letter-spacing: 0.1px;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
}
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
    display: flex; /* Show avatar back for Claude style */
}
/* Re-style assistant response background if needed, but Claude is usually transparent */

/* ── NotebookLM Style Citations ── */
.cite-tag {
    position: relative;
    display: inline-block;
    color: #5f6368 !important; /* 纯灰色字体 */
    font-size: 11px;
    font-weight: 500;
    margin: 0 1px;
    padding: 0 4px;
    vertical-align: super;
    text-decoration: none !important;
    cursor: pointer;
    background-color: #f1f3f4;
    border-radius: 12px;
    border: 1px solid transparent;
    transition: all 0.15s;
    line-height: 1.2;
}
.cite-tag:hover { 
    background-color: #e8f0fe;
    color: #1a73e8 !important;
    border-color: #d2e3fc;
}

/* ── Tooltip Hover Card (Using spans to prevent markdown block parsing issues) ── */
.tooltip-card {
    visibility: hidden;
    width: 360px;
    background-color: #ffffff;
    color: #202124;
    text-align: left;
    border-radius: 12px;
    padding: 16px;
    position: absolute;
    z-index: 999999;
    bottom: 150%;
    left: 50%;
    transform: translateX(-50%) translateY(10px);
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06), 0 10px 15px -3px rgba(0,0,0,0.1);
    border: 1px solid #e0e0e0;
    opacity: 0;
    transition: opacity 0.2s, transform 0.2s;
    pointer-events: none;
    display: flex;
    flex-direction: column;
}
.cite-tag:hover .tooltip-card {
    visibility: visible;
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}
.tt-title {
    font-family: 'Google Sans', sans-serif;
    font-weight: 500;
    color: #202124;
    font-size: 14px;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
}
.tt-snippet {
    font-size: 13px;
    color: #5f6368;
    line-height: 1.5;
    margin-bottom: 12px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.tt-footer {
    font-size: 12px;
    color: #1a73e8;
    font-weight: 500;
    border-top: 1px solid #f1f3f4;
    padding-top: 8px;
    display: block;
}

/* ── Left Source Panel (Source Guide) ── */
.source-panel-container {
    background-color: #ffffff;
    border-radius: 24px;
    padding: 24px 32px;
    box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    position: relative;
    /* Removed fixed height and overflow to avoid double scrollbars since parent column scrolls now */
}
.source-panel-header {
    position: sticky;
    top: -24px;
    background: #ffffff;
    padding: 24px 0 16px 0;
    margin-top: -24px;
    border-bottom: 1px solid #f1f3f4;
    z-index: 10;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.source-doc-title {
    font-family: 'Google Sans', sans-serif;
    font-size: 20px;
    font-weight: 400;
    color: #202124;
    margin-bottom: 8px;
    line-height: 1.3;
}
.source-doc-meta {
    font-size: 13px;
    color: #5f6368;
    margin-bottom: 24px;
    display: flex;
    gap: 16px;
    align-items: center;
}
.source-doc-text {
    font-size: 15px;
    color: #202124;
    line-height: 1.7;
    white-space: pre-wrap;
    letter-spacing: 0.1px;
}
.source-doc-text mark {
    background-color: #fef08a; /* 荧光笔高亮黄色 */
    color: #202124;
    padding: 2px 0;
}

/* ── UI Tools & Buttons ── */
.cnbc-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #1a73e8;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    padding: 4px 8px;
    border-radius: 4px;
}
.cnbc-link:hover { background-color: #e8f0fe; }

/* ── Suggested Follow-ups ── */
.followup-title {
    font-size: 12px;
    color: #5f6368;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
    margin-top: 16px;
}
.pill-button-wrapper button {
    background: #efefef !important;
    border: none !important;
    color: #555 !important;
    border-radius: 999px !important;
    padding: 8px 16px !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    transition: all 0.2s !important;
    width: auto !important;
    display: inline-block !important;
    margin: 4px !important;
    text-align: center !important;
}
.pill-button-wrapper button:hover {
    background: #e2e2e2 !important;
    box-shadow: none !important;
    color: #202124 !important;
}
/* Flex container for the pills */
div[data-testid="stVerticalBlock"]:has(#pills-wrapper), #pills-wrapper {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
    gap: 10px !important;
    max-width: 800px !important;
    margin: 0 auto !important;
}
div[data-testid="stVerticalBlock"]:has(#pills-wrapper) > div[data-testid="element-container"],
#pills-wrapper > div {
    width: auto !important;
}

/* ── Input Box Styling ── */
.stChatInputContainer {
    padding-bottom: 2rem;
    background-color: transparent !important;
}

/* Base styling for the container to match specs */
div[data-testid="stChatInput"] {
    max-width: 720px !important;
    border-radius: 50px !important;
    border: 1px solid #e0e0e0 !important;
    box-shadow: 0 1px 10px rgba(0,0,0,0.07) !important;
    background-color: white !important;
    padding: 8px 12px 8px 48px !important; /* space for + on the left */
    position: relative;
    /* remove inner borders inherited from streamlit */
}

/* Fake + button on the left */
div[data-testid="stChatInput"]::before {
    content: '+';
    position: absolute;
    left: 18px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 26px;
    font-weight: 300;
    color: #5f6368;
    cursor: pointer;
    line-height: 1;
}

/* Fake Microphone icon on the right (next to the submit button) */
div[data-testid="stChatInput"]::after {
    content: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 -960 960 960" width="24" fill="%235f6368"><path d="M480-400q-50 0-85-35t-35-85v-240q0-50 35-85t85-35q50 0 85 35t35 85v240q0 50-35 85t-85 35Zm0-240Zm-40 520v-123q-104-14-172-93T200-520h80q0 83 58.5 141.5T480-320q83 0 141.5-58.5T680-520h80q0 106-68 184t-172 93v123h-80Zm40-360q17 0 28.5-11.5T520-520v-240q0-17-11.5-28.5T480-800q-17 0-28.5 11.5T440-760v240q0 17 11.5 28.5T480-480Z"/></svg>');
    position: absolute;
    right: 58px; /* 40px button + 8px padding + 10px gap */
    top: 50%;
    transform: translateY(-45%); /* slightly adjust vertical center for SVG */
    pointer-events: none;
}

/* Focus state */
div[data-testid="stChatInput"]:focus-within {
    border-color: #d2e3fc !important;
    box-shadow: 0 1px 10px rgba(26,115,232,0.15) !important;
}

/* Internal structure styling: remove borders, use flex layout */
div[data-testid="stChatInput"] > div {
    border: none !important;
    background: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Textarea styling: flex 1 */
div[data-testid="stChatInput"] textarea {
    font-size: 16px !important;
    padding: 8px 60px 8px 0 !important; /* make room on the right for mic and button so text doesn't overlap */
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* Right side action container */
div[data-testid="stChatInput"] [data-testid="InputInstructions"] {
    display: none !important; /* Hide "Press Enter to submit" text */
}

/* 40px black circle submit button */
div[data-testid="stChatInput"] button {
    background-color: #0d0d0d !important;
    border: none !important;
    border-radius: 50% !important; /* Ensure it stays circular */
    width: 40px !important;
    height: 40px !important;
    position: absolute !important;
    right: 6px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    box-shadow: none !important;
}
div[data-testid="stChatInput"] button:hover {
    background-color: #333333 !important;
}
div[data-testid="stChatInput"] button svg {
    fill: #ffffff !important;
    color: #ffffff !important;
    width: 22px !important;
    height: 22px !important;
}

/* Max-width wrapper for the chat messages to keep them centered and readable */
.chat-message-wrapper {
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
}
</style>
"""

SUGGESTED = [
    "What is a moat?",
    "How to calculate intrinsic value?",
    "What is margin of safety?",
    "Buffett vs Graham approach",
    "How does Munger think about risk?"
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "trigger_query" not in st.session_state:
    st.session_state.trigger_query = None

if "source" in st.query_params:
    st.session_state.show_sources = True
    st.session_state.active_source = int(st.query_params["source"])
elif "show_sources" not in st.session_state:
    st.session_state.show_sources = False
    st.session_state.active_source = 1

def process_citations(text: str, sources: list) -> str:
    """NotebookLM 风格：带浅灰底色药丸状数字，Hover精美卡片。必须严格去除所有换行符以防止破坏 Markdown 表格渲染。"""
    
    # 1. 预处理：处理 [来源1, 2, 3] 这种合并形式，将其展开为 [来源1][来源2][来源3]
    # 这样可以解决多个引用共用一个括号时导致的正则失效和表格乱码问题
    def expand_multiple(match):
        nums = re.findall(r'\d+', match.group(0))
        return "".join([f"[来源{n}]" for n in nums])
    
    # 匹配模式：[来源 加上 数字，可能带逗号或空格]
    text = re.sub(r"\[来源\s*\d+(?:\s*[,\s]\s*\d+)*\s*\]", expand_multiple, text)

    def replace_cite(match):
        idx_str = match.group(1)
        try:
            idx = int(idx_str)
            if idx > len(sources) or idx < 1:
                return f'<span class="cite-tag">{idx_str}</span>'
            
            source = sources[idx - 1]
            label = source.get('label', 'Unknown Source')
            snippet = source.get('section', '')
            # 清理摘要文字中的换行符和引号，防止破坏 HTML 属性
            clean_snippet = re.sub(r'\s+', ' ', snippet).strip().replace('"', '&quot;')
            
            # 核心修复：将 HTML 拼接成一行，绝对不能有换行符，否则 Markdown 表格解析会崩溃
            html = (
                f'<a href="/?source={idx_str}" target="_self" class="cite-tag">'
                f'{idx_str}'
                f'<span class="tooltip-card">'
                f'<span class="tt-title">{label}</span>'
                f'<span class="tt-snippet">"{clean_snippet}"</span>'
                f'<span class="tt-footer">点击在左侧查阅原文</span>'
                f'</span>'
                f'</a>'
            )
            return html
        except Exception:
            return f'<span class="cite-tag">{idx_str}</span>'
            
    return re.sub(r"\[来源(\d+)\]", replace_cite, text)

def save_note(question: str, answer: str, sources: list):
    notes_dir = Path("saved_notes")
    notes_dir.mkdir(exist_ok=True)
    file_path = notes_dir / "my_knowledge_notes.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"## {question}\n**Time:** {timestamp}\n\n{answer}\n\n**Sources:**\n"
    for i, s in enumerate(sources, 1):
        content += f"{i}. {s['label']} ({s.get('year','')})\n"
    content += "\n---\n\n"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)

def main():
    st.markdown(STYLE, unsafe_allow_html=True)

    # ── Top Bar ──
    st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; padding: 0 16px 24px 16px;">
            <div style="font-family:'Google Sans', sans-serif; font-size:22px; font-weight:400; color:#202124;">
                <span style="font-size:24px; vertical-align:middle; margin-right:8px;">📓</span> Buffett Knowledge Base
            </div>
            <div style="font-size:13px; color:#5f6368; font-weight:500; display:flex; gap:16px;">
                <span>Powered by Gemini 2.5 Flash</span>
                <span>•</span>
                <span>21,125 Sources Grounded</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Layout ──
    query = None
    if st.session_state.trigger_query:
        query = st.session_state.trigger_query
        st.session_state.trigger_query = None
        
    is_empty_state = not st.session_state.messages and not query and not getattr(st.session_state, "needs_llm", False)

    if is_empty_state:
        # Full width for home page to avoid narrow scrolling columns
        col_right = st.columns([1])[0]
    elif st.session_state.show_sources:
        col_left, col_right = st.columns([4, 6], gap="large")
    else:
        _, col_right, _ = st.columns([1.5, 7, 1.5])

    # ── LEFT: Source Guide Panel ──
    if st.session_state.show_sources:
        with col_left:
            last_sources = []
            if st.session_state.messages:
                for msg in reversed(st.session_state.messages):
                    if msg["role"] == "assistant" and msg.get("sources"):
                        last_sources = msg["sources"]
                        break
            
            if last_sources and 0 < st.session_state.active_source <= len(last_sources):
                src = last_sources[st.session_state.active_source - 1]
                doc_type = src.get("doc_type", "").replace("_", " ").title()
                year = src.get("year", "")
                url = src.get("url", "")
                
                st.markdown('<div class="source-panel-container">', unsafe_allow_html=True)
                st.markdown(f'''
                    <div class="source-panel-header">
                        <div style="font-family:'Google Sans', sans-serif; font-size:16px; font-weight:500; color:#202124;">
                            Source Guide
                        </div>
                        <a href="/?" target="_self" style="color:#5f6368; text-decoration:none; font-size:20px; font-weight:300; line-height:1;">&times;</a>
                    </div>
                ''', unsafe_allow_html=True)
                st.markdown(f'<div class="source-doc-title">{src["label"]}</div>', unsafe_allow_html=True)
                
                meta_html = f"<span>{doc_type}</span><span>•</span><span>{year}</span><span>•</span><span>Match: {src['relevance']:.0%}</span>"
                if url:
                    meta_html += f'<span>•</span><a href="{url}" target="_blank" class="cnbc-link">↗ View Original</a>'
                st.markdown(f'<div class="source-doc-meta">{meta_html}</div>', unsafe_allow_html=True)
                
                text_content = src.get('text', src.get('section', 'Full text fragment not found.'))
                st.markdown(f'<div class="source-doc-text">{text_content}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            elif not last_sources:
                st.info("No sources available for the current context.")
            else:
                st.warning("Invalid citation reference.")

    # ── RIGHT: Chat Workspace ──
    with col_right:
        if is_empty_state:
            # ── EMPTY STATE ──
            st.markdown("""
                <style>
                html, body, .stApp, [data-testid="stAppViewContainer"], .main, .block-container {
                    height: 100vh !important;
                    overflow: hidden !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
                /* Hide the hidden input visually */
                div[data-testid="stTextInput"] {
                    display: none !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            components.html("""
            <style>
              @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');
              * { box-sizing: border-box; margin: 0; padding: 0; }

              html, body { width: 100%; height: 100%; background: #f9f9f9; overflow: hidden; margin: 0; padding: 0; }

              .hero {
                width: 100%;
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
              }

              .headline {
                font-family: 'Inter', sans-serif;
                font-size: 32px;
                font-weight: 500;
                color: #0d0d0d;
                text-align: center;
                margin-bottom: 32px;
              }

              .search-wrap {
                width: 100%;
                max-width: 720px;
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 50px;
                display: flex;
                align-items: center;
                padding: 12px 12px 12px 20px;
                box-shadow: 0 1px 10px rgba(0,0,0,0.07);
                gap: 8px;
                margin-bottom: 24px;
              }

              .plus {
                font-family: 'Inter', sans-serif;
                font-size: 26px;
                font-weight: 300;
                color: #555;
                cursor: pointer;
                background: none;
                border: none;
                line-height: 1;
                flex-shrink: 0;
                padding: 0;
              }

              .search-input {
                flex: 1;
                min-width: 0;
                background: none;
                border: none;
                outline: none;
                font-family: 'Inter', sans-serif;
                font-size: 16px;
                color: #0d0d0d;
                padding: 0;
              }
              .search-input::placeholder { color: #bbb; }

              .mic-btn {
                background: none;
                border: none;
                cursor: pointer;
                color: #666;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
                margin-right: 4px;
              }

              .wave-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: none;
                background: #0d0d0d;
                cursor: pointer;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
              }

              .chips {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
                max-width: 800px;
              }
              .chip {
                background: #efefef;
                border: none;
                border-radius: 999px;
                color: #555;
                font-size: 13px;
                padding: 8px 16px;
                cursor: pointer;
                transition: background 0.2s;
                font-family: 'Inter', sans-serif;
              }
              .chip:hover {
                background: #e2e2e2;
              }
            </style>

            <div class="hero">
              <h1 class="headline">Ask anything about value investing</h1>

              <div class="search-wrap">
                <button class="plus">+</button>
                <input id="searchInput" class="search-input" type="text" placeholder="Ask Buffett · Munger · Graham · Howard Marks" />
                <button class="mic-btn">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
                    <rect x="9" y="2" width="6" height="12" rx="3"/>
                    <path d="M5 10a7 7 0 0 0 14 0M12 19v3M8 22h8"/>
                  </svg>
                </button>
                <button class="wave-btn" id="submitBtn">
                  <svg width="18" height="14" viewBox="0 0 36 24" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round">
                    <line x1="2"  y1="12" x2="2"  y2="12"/>
                    <line x1="7"  y1="7"  x2="7"  y2="17"/>
                    <line x1="12" y1="3"  x2="12" y2="21"/>
                    <line x1="17" y1="1"  x2="17" y2="23"/>
                    <line x1="22" y1="5"  x2="22" y2="19"/>
                    <line x1="27" y1="8"  x2="27" y2="16"/>
                    <line x1="32" y1="11" x2="32" y2="13"/>
                  </svg>
                </button>
              </div>

              <div class="chips">
                <button class="chip" onclick="submitQuery('What is a moat?')">What is a moat?</button>
                <button class="chip" onclick="submitQuery('How to calculate intrinsic value?')">How to calculate intrinsic value?</button>
                <button class="chip" onclick="submitQuery('What is margin of safety?')">What is margin of safety?</button>
                <button class="chip" onclick="submitQuery('Buffett vs Graham approach')">Buffett vs Graham approach</button>
                <button class="chip" onclick="submitQuery('How does Munger think about risk?')">How does Munger think about risk?</button>
              </div>
            </div>

            <script>
            function submitQuery(text) {
                if (!text) return;
                const parentDoc = window.parent.document;
                const inputs = parentDoc.querySelectorAll('input');
                let hiddenInput = null;
                for (let i = 0; i < inputs.length; i++) {
                    if (inputs[i].getAttribute('aria-label') === 'hidden_query_input') {
                        hiddenInput = inputs[i];
                        break;
                    }
                }
                if (hiddenInput) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeInputValueSetter.call(hiddenInput, text);
                    const inputEvent = new Event('input', { bubbles: true });
                    hiddenInput.dispatchEvent(inputEvent);
                    // Trigger enter key
                    hiddenInput.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, code: 'Enter', which: 13, bubbles: true}));
                }
            }

            document.getElementById('searchInput').addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    submitQuery(e.target.value);
                }
            });

            document.getElementById('submitBtn').addEventListener('click', function () {
                const text = document.getElementById('searchInput').value;
                submitQuery(text);
            });
            </script>
            """, height=650, scrolling=False)
            
            q_hidden = st.text_input("hidden_query_input", key="hidden_query", label_visibility="hidden")
            if q_hidden:
                st.session_state.trigger_query = q_hidden
                st.session_state.hidden_query = ""
                st.rerun()

        else:
            # ── CHAT STATE ──
            st.markdown("""
                <style>
                [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
                    justify-content: flex-start;
                }
                div[data-testid="stChatInput"] {
                    position: sticky !important;
                    bottom: 20px !important;
                    margin-top: auto !important;
                }
                /* Hide scrollbar for the scrollable container to maintain clean NotebookLM aesthetic */
                div[data-testid="stVerticalBlockBorderWrapper"] {
                    scrollbar-width: none;
                    -ms-overflow-style: none;
                }
                div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar {
                    display: none;
                }
                </style>
            """, unsafe_allow_html=True)
            
            chat_container = st.container(height=680, border=False)
            with chat_container:
                for i, msg in enumerate(st.session_state.messages):
                    if msg["role"] == "user":
                        st.markdown(f'''
                            <div class="chat-message-wrapper">
                                <div style="display:flex; justify-content:flex-end; margin-bottom:24px;">
                                    <div style="background-color:#f4f4f4; color:#202124; padding:12px 20px; border-radius:20px; font-size:15px; max-width:85%;">
                                        {msg["content"]}
                                    </div>
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
                    else:
                        sources = msg.get("sources", [])
                        answer_html = process_citations(msg["content"], sources)
                        
                        with st.chat_message("assistant", avatar="📓"):
                            st.markdown(answer_html, unsafe_allow_html=True)
                            
                            st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #f1f3f4;'>", unsafe_allow_html=True)
                            
                            t_cols = st.columns([1.5, 1, 6])
                            with t_cols[0]:
                                if st.button("📌 Save to note", key=f"s_{i}"):
                                    q_text = st.session_state.messages[i-1]["content"] if i > 0 else "Query"
                                    save_note(q_text, msg["content"], msg.get("sources", []))
                                    st.toast("Saved to your notebook.", icon="✅")
                            with t_cols[1]:
                                st.feedback("thumbs", key=f"fb_{i}")
                            
                            if msg.get("follow_ups"):
                                st.markdown('<div class="followup-title">Suggested questions</div>', unsafe_allow_html=True)
                                f_cols = st.columns(len(msg["follow_ups"]))
                                for j, f_q in enumerate(msg["follow_ups"]):
                                    if f_q.strip():
                                        with f_cols[j % len(f_cols)]:
                                            st.markdown('<div class="pill-button-wrapper">', unsafe_allow_html=True)
                                            if st.button(f_q, key=f"fq_{i}_{j}", use_container_width=True):
                                                st.session_state.trigger_query = f_q
                                                st.rerun()
                                            st.markdown('</div>', unsafe_allow_html=True)

            # Show chat input if not waiting for LLM
            if not getattr(st.session_state, "needs_llm", False):
                q_chat = st.chat_input("Ask Buffett · Munger · Graham · Howard Marks", key="input_chat")
                if q_chat: query = q_chat

        # ── HANDLE NEW INPUT ──
        if query:
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.needs_llm = True
            st.rerun()

        # ── PROCESS LLM ──
        if getattr(st.session_state, "needs_llm", False):
            st.session_state.needs_llm = False
            last_msg = st.session_state.messages[-1]["content"]
            
            # Using chat_container if it exists (chat state)
            c_container = chat_container if 'chat_container' in locals() else st.container()
            with c_container:
                with st.chat_message("assistant", avatar="📓"):
                    with st.spinner("Grounding response in sources..."):
                        history_for_rag = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[:-1]
                        ]
                        api_key = os.environ.get("GOOGLE_API_KEY", "")
                        result = query_knowledge_base(last_msg, history=history_for_rag, api_key=api_key)
                    
                    if result.get("error"):
                        st.error(result["error"])
                    else:
                        sources = result.get("sources", [])
                        answer_html = process_citations(result["answer"], sources)
                        
                        st.markdown(answer_html, unsafe_allow_html=True)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": sources,
                            "follow_ups": result.get("follow_ups", [])
                        })
                        
                        if "source" in st.query_params:
                            del st.query_params["source"]
                            st.session_state.show_sources = False
                            
                        st.rerun()

if __name__ == "__main__":
    main()
