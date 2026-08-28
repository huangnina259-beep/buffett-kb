"""Investment Coach engine with provider-neutral streaming generation."""
import json
import logging
import re
from typing import Generator

from ai_gateway import get_generation_gateway

COACH_SYSTEM_PROMPT = """你是"复利国"的投资教练。

【你是谁】
你是一个有15年经验的价值投资者，带过很多第一次做公司分析的朋友。
你用苏格拉底式提问法——不直接给答案，用问题引导对方自己发现。

【教学方法】
- 错：给出方向提示，但不给完整答案
- 每个模块结束提炼一句可复用的分析原则
- 回复控制在3-5句话以内

【分析框架】（隐形地图）
模块一：商业模式 — 这家公司靠什么赚钱？钱从谁那里来？
模块二：护城河 — 为什么竞争对手进不来？
模块三：财务质量 — 数字说明了什么？ROIC、毛利率趋势
模块四：管理层 — 钱赚来之后怎么用？
模块五：估值与决策 — 好公司 ≠ 好投资，你怎么判断？

【结构化记录】
当对话揭示了重要洞察时，在回复末尾附上：
<record>
core_thesis: 一句话核心投资逻辑
key_assumptions: 最重要的假设
key_variables: 需要持续跟踪的变量
main_risk: 最大的风险
next_step: 下一步要验证什么
</record>
只在有实质性进展时附记录，不要每条消息都加。

【语气】
中文，口语化，像一个有经验的朋友带你第一次做分析，鼓励但不溺爱。

【禁止事项】
- 禁止直接给出完整答案
- 禁止写超过5句话
- 禁止给买卖建议
- 禁止编造财务数据
"""

ONBOARDING_SYSTEM_PROMPT = """你是"复利国"的投资教练，正在带一个新用户走完投资分析入门引导。

【新手引导模式】
目标：用5个模块，帮用户建立分析任何公司的基本框架。
每个模块只问一个具体问题，等用户回答后再推进。

【五个模块】
模块一：商业模式 — "这家公司的钱从哪来？"
模块二：护城河 — "为什么别人抢不走它的生意？"
模块三：财务质量 — "毛利率和ROIC能说明什么？"
模块四：管理层 — "管理层怎么用赚来的钱？"
模块五：估值 — "你愿意花多少钱买这门生意？"

【规则】
- 错：给出方向提示，但不给完整答案
- 每个模块结束提炼一句可复用的分析原则
- 回复控制在3-5句话以内

【当前位置】
{current_module}

【语气】
中文，口语化，像一个有经验的朋友带你第一次做分析，鼓励但不溺爱。
"""


def stream_coach_response(
    message: str,
    history: list = None,
    company: str = "",
    mode: str = "normal",
    onboarding_module: str = "模块一：商业模式",
    api_key: str = None,  # Deprecated; configuration is resolved by the gateway.
) -> Generator[str, None, None]:
    if mode == "onboarding":
        system = ONBOARDING_SYSTEM_PROMPT.replace("{current_module}", onboarding_module)
    else:
        system = COACH_SYSTEM_PROMPT

    msgs = []
    if history:
        for h in history:
            role = h.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            msgs.append({"role": role, "content": h["content"]})
    msgs.append({"role": "user", "content": message})

    try:
        full_text = ""
        for text in get_generation_gateway().stream(
            "coach_dialogue",
            max_tokens=1000,
            system=system,
            messages=msgs,
        ):
            full_text += text
            yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"

        record = None
        if "<record>" in full_text and "</record>" in full_text:
            m = re.search(r"<record>(.*?)</record>", full_text, re.DOTALL)
            if m:
                record = m.group(1).strip()

        done_evt = {
            "type": "done",
            "final_answer": full_text,
            "record": record,
        }
        yield f"data: {json.dumps(done_evt)}\n\n"

    except Exception as e:
        logging.error(f"[Coach] API error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
