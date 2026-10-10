"""ToolParamCheckSkill —— Mid-Hook：Agent 调用任意工具前做参数强校验。

职责（P0）：
1. 基于 Pydantic 模型做参数强校验。
2. 自动清洗字符串首尾空格。
3. 校验：必填项、字符串长度、数值范围、枚举。
4. 参数非法返回结构化错误信息，支持 Agent 重试。
红线对齐：工具调用参数经过 Schema/Pydantic 校验（检查清单第 5 节）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from pydantic import BaseModel, ValidationError

from .security_log_skill import SecurityLogSkill


@dataclass
class ToolParamCheckResult:
    blocked: bool
    reason: str
    raw_params: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)


class ToolParamCheckSkill:
    """基于 Pydantic 模型的参数强校验。"""

    def __init__(self, param_model: type[BaseModel], enable: bool = True):
        self.enable = enable
        self.param_model = param_model

    def run(self, session_id: str, raw_params: Dict[str, Any]) -> ToolParamCheckResult:
        if not self.enable:
            return ToolParamCheckResult(
                blocked=False,
                reason="skill disabled",
                raw_params=raw_params or {},
                meta={},
            )

        blocked = False
        reason = ""
        meta: Dict[str, Any] = {}

        try:
            # 自动清洗：字符串去首尾空格
            cleaned: Dict[str, Any] = {}
            for k, v in (raw_params or {}).items():
                cleaned[k] = v.strip() if isinstance(v, str) else v
            self.param_model(**cleaned)
        except ValidationError as e:
            blocked = True
            reason = f"工具参数校验失败: {e.errors()}"
            meta["errors"] = e.errors()
        except TypeError as e:
            blocked = True
            reason = f"工具参数类型错误: {str(e)}"
            meta["errors"] = [str(e)]

        SecurityLogSkill.log_security_event(
            event_type="TOOL_PARAM_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"raw_params": raw_params or {}},
        )

        return ToolParamCheckResult(
            blocked=blocked,
            reason=reason,
            raw_params=raw_params or {},
            meta=meta,
        )