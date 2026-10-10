"""JsonSchemaCheckSkill —— Mid-Hook：LLM 输出结构化 JSON 之后、工具调用之前。

职责（P0）：
1. 自动剥离 markdown ```json 代码块标记。
2. JSON 解析 + jsonschema 强校验（必填字段、类型、枚举）。
3. 无法修复的 JSON 格式错误直接阻断。
红线对齐：工具调用参数经过 Schema/Pydantic 校验（检查清单第 5 节）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from jsonschema import validate, ValidationError

from .security_log_skill import SecurityLogSkill


@dataclass
class JsonSchemaCheckResult:
    blocked: bool
    reason: str
    raw_text: str
    parsed_json: Optional[Dict[str, Any]]
    meta: Dict[str, Any] = field(default_factory=dict)


# 匹配 ```json ... ``` / ``` ... ``` markdown 代码块（含可选 json 语言标记）。
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S | re.IGNORECASE)


class JsonSchemaCheckSkill:
    """JSON 解析 + jsonschema 强校验。"""

    def __init__(self, schema: Dict[str, Any], enable: bool = True):
        self.enable = enable
        self.schema = schema

    def _extract_json(self, text: str) -> str:
        match = _CODE_BLOCK_RE.search(text or "")
        if match:
            return match.group(1).strip()
        return (text or "").strip()

    def run(self, session_id: str, raw_text: str) -> JsonSchemaCheckResult:
        if not self.enable:
            return JsonSchemaCheckResult(
                blocked=False,
                reason="skill disabled",
                raw_text=raw_text,
                parsed_json=None,
                meta={},
            )

        blocked = False
        reason = ""
        parsed: Optional[Dict[str, Any]] = None
        meta: Dict[str, Any] = {}

        try:
            json_str = self._extract_json(raw_text)
            parsed = json.loads(json_str)
            validate(instance=parsed, schema=self.schema)
        except json.JSONDecodeError as e:
            blocked = True
            reason = f"JSON解析失败: {str(e)}"
        except ValidationError as e:
            blocked = True
            reason = f"Schema校验不通过: {e.message}"
        except TypeError as e:
            blocked = True
            reason = f"Schema类型错误: {str(e)}"

        SecurityLogSkill.log_security_event(
            event_type="JSON_SCHEMA_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"raw_text_preview": (raw_text or "")[:200]},
        )

        return JsonSchemaCheckResult(
            blocked=blocked,
            reason=reason,
            raw_text=raw_text,
            parsed_json=parsed,
            meta=meta,
        )