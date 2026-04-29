import asyncio
import json
import re
from typing import Dict

from openai import AsyncOpenAI

from backend.core.config import Settings


ALLOWED_EXPRESSIONS = {
    "neutral",
    "warm",
    "happy",
    "thinking",
    "serious",
    "surprised",
    "apologetic",
    "encouraging",
}

ALLOWED_MOTIONS = {
    "idle",
    "explain",
    "nod",
    "emphasize",
    "magic",
    "encourage",
    "celebrate",
}


class ActionPlanner:
    def __init__(self, settings: Settings, client: AsyncOpenAI):
        self.settings = settings
        self.client = client

    async def plan(self, sentence: str) -> Dict[str, str]:
        if self.settings.enable_llm_actions:
            planned = await self._plan_with_llm(sentence)
            if planned:
                return planned
        return self._plan_with_rules(sentence)

    def _plan_with_rules(self, sentence: str) -> Dict[str, str]:
        text = sentence.strip()
        if not text:
            return {"expression": "neutral", "motion": "idle", "style": "normal", "reason": "empty"}

        if re.search(r"抱歉|无法|不能|错误|失败|没有找到|不确定", text):
            return {"expression": "apologetic", "motion": "nod", "style": "soft", "reason": "apology_or_uncertainty"}
        if re.search(r"注意|必须|严禁|不得|警告|风险|处分|影响", text):
            return {"expression": "serious", "motion": "emphasize", "style": "serious", "reason": "important_notice"}
        if re.search(r"可以|建议|步骤|首先|其次|最后|流程|办法|需要", text):
            return {"expression": "warm", "motion": "explain", "style": "normal", "reason": "explanation"}
        if re.search(r"恭喜|很好|完成|通过|成功|优秀", text):
            return {"expression": "happy", "motion": "celebrate", "style": "bright", "reason": "positive"}
        if re.search(r"可能|大概|我来|查询|检索|分析", text):
            return {"expression": "thinking", "motion": "idle", "style": "thinking", "reason": "thinking"}
        return {"expression": "warm", "motion": "nod", "style": "normal", "reason": "default"}

    async def _plan_with_llm(self, sentence: str) -> Dict[str, str] | None:
        prompt = (
            "You select expression and motion labels for a Live2D digital human. "
            f"Allowed expressions: {sorted(ALLOWED_EXPRESSIONS)}. "
            f"Allowed motions: {sorted(ALLOWED_MOTIONS)}. "
            "Return only JSON with expression, motion, style, reason."
        )
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.settings.resolved_chat_model,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": sentence},
                    ],
                ),
                timeout=self.settings.llm_timeout_sec,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
            data = json.loads(raw)
            expression = data.get("expression", "warm")
            motion = data.get("motion", "explain")
            if expression not in ALLOWED_EXPRESSIONS:
                expression = "warm"
            if motion not in ALLOWED_MOTIONS:
                motion = "explain"
            return {
                "expression": expression,
                "motion": motion,
                "style": data.get("style", "normal"),
                "reason": data.get("reason", "llm"),
            }
        except Exception:
            return None
