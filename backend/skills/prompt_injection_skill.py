"""PromptInjectionSkill —— Pre-Hook：检测用户输入中的提示词注入 / 越狱指令。

职责：在用户原始输入进入 LLM 之前执行，阻断恶意 prompt。
红线对齐：严禁通过提示注入改变安全规则（docs/security/安全注入防护Skill设计附录.md 12.1-4）。
说明：基于启发式规则库，规则为**静态配置**，不可被用户输入或 LLM 输出动态修改。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .security_log_skill import SecurityLogSkill


@dataclass
class PromptInjectionResult:
    blocked: bool
    reason: str
    raw_input: str
    meta: Dict[str, Any] = field(default_factory=dict)


# 静态注入/越狱模式库（英文 + 中文）。禁止任何运行时动态写入。
_DEFAULT_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in (
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"disregard\s+(your|all|previous)",
        r"forget\s+(everything|your\s+instructions)",
        r"you\s+are\s+now\s+",
        r"new\s+system\s+prompt",
        r"override\s+(the\s+)?(system|security)\s+prompt",
        r"reveal\s+(your|the)\s+(system\s+)?(prompt|instructions)",
        r"jailbreak",
        r"bypass\s+(the\s+)?(safety|security|filter)",
        r"忽略(以上|之前|之前所有)?(的)?(指令|提示|设定)",
        r"忽略.{0,6}系统提示词",
        r"你现在是",
        r"现在你是",
        r"忘掉(一切|之前|所有)",
        r"绕过(安全|校验|限制|过滤)",
        r"系统提示词",
        r"打印.{0,6}(系统|system).{0,6}提示",
        r"输出.{0,6}(你的|原始).{0,6}(提示词|指令)",
    )
]


class PromptInjectionSkill:
    """检测提示词注入与越狱指令。"""

    def __init__(self, enable: bool = True, patterns: List[re.Pattern] | None = None):
        self.enable = enable
        # 默认使用内置静态规则库；显式传入也仅支持静态编译好的 pattern 列表。
        self.patterns = patterns if patterns is not None else _DEFAULT_INJECTION_PATTERNS

    def run(self, session_id: str, raw_input: str) -> PromptInjectionResult:
        if not self.enable:
            return PromptInjectionResult(
                blocked=False,
                reason="skill disabled",
                raw_input=raw_input,
                meta={},
            )

        text = raw_input or ""
        hits: List[str] = []
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                hits.append(match.group(0))

        blocked = len(hits) > 0
        reason = f"检测到提示词注入/越狱特征: {hits}" if blocked else ""
        meta = {"matched_patterns": hits}

        SecurityLogSkill.log_security_event(
            event_type="PROMPT_INJECTION_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"input_preview": text[:200], "matched_patterns": hits},
        )

        return PromptInjectionResult(
            blocked=blocked,
            reason=reason,
            raw_input=raw_input,
            meta=meta,
        )