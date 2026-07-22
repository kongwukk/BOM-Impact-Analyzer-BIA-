import json
import re
from typing import Any

import httpx

from app.core.config import Settings, settings
from app.schemas.query import QueryPlan

SYSTEM_PROMPT = """你是BOM数据库查询规划器，只负责把用户问题转换成查询条件。
不得回答问题、不得生成SQL、不得臆造数据库中不存在的数据。
只输出一个JSON对象，字段必须来自下面的结构：
{
  "intent": "impact|component_search|product_search",
  "manufacturer": "制造商或null",
  "part_number": "元器件完整或部分型号或null",
  "product_code": "产品型号或null",
  "keywords": ["用于匹配元器件描述的简短关键词"],
  "lifecycle_status": "Active|NRND|EOL|null",
  "critical_only": false
}
TI统一为Texas Instruments，ST统一为STMicroelectronics。不要把“哪些产品、BOM、元器件、芯片、影响”放入keywords。
"""


class LlmError(RuntimeError):
    pass


class LlmQueryInterpreter:
    """OpenAI-compatible structured intent extractor.

    The model never receives database credentials and never produces executable SQL.
    """

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def interpret(self, question: str) -> QueryPlan:
        if not self.config.llm_available:
            raise LlmError("大模型尚未配置")
        url = f"{self.config.llm_base_url.rstrip('/')}/chat/completions"
        try:
            with httpx.Client(timeout=self.config.llm_timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.config.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.llm_model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": question},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LlmError("大模型意图解析请求失败") from exc
        try:
            return QueryPlan.model_validate(_json_object(content))
        except (ValueError, TypeError) as exc:
            raise LlmError("大模型返回了无效的查询条件") from exc


def _json_object(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    text = str(content).strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value
