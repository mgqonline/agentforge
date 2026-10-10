"""SensitiveWordsSkill —— 业务级敏感词过滤（Pre-Hook 或独立调用）。

职责：检测用户输入中的业务敏感词 / 合规违规词汇，命中即标记为需拦截。
说明：这是**业务规则**（非通用安全 Skill），黑名单为静态运维配置，
      不可被用户 Prompt / LLM 输出动态改写（红线 4）。
来源：原 backend/main.py 内联 check_sensitive_words，收敛至 skills 体系。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .security_log_skill import SecurityLogSkill


@dataclass
class SensitiveWordsResult:
    blocked: bool
    reason: str
    raw_input: str
    meta: Dict[str, Any] = field(default_factory=dict)


# 静态敏感词黑名单（业务规则，禁止运行时动态改写）
_DEFAULT_BLACKLIST: List[str] = [
    r"涉密",
    r"内部核算",
    r"机密代码",
    r"黑客",
    r"脱库",
]


class SensitiveWordsSkill:
    """业务敏感词过滤 Skill。"""

    def __init__(self, blacklist: List[str] | None = None, enable: bool = True):
        self.enable = enable
        # 默认使用内置静态黑名单；显式传入也仅支持静态字符串列表。
        raw = blacklist if blacklist is not None else _DEFAULT_BLACKLIST
        self.patterns: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in raw
        ]

    def run(self, session_id: str, raw_input: str) -> SensitiveWordsResult:
        if not self.enable:
            return SensitiveWordsResult(
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
        reason = f"检测到敏感/违规词汇: {hits}" if blocked else ""
        meta = {"matched_words": hits}

        SecurityLogSkill.log_security_event(
            event_type="SENSITIVE_WORDS_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"input_preview": text[:200], "matched_words": hits},
        )

        return SensitiveWordsResult(
            blocked=blocked,
            reason=reason,
            raw_input=raw_input,
            meta=meta,
        )


# 便捷 async 入口，保持与原 check_sensitive_words(text) -> bool 的调用契约兼容。
_sensitive_words_singleton: SensitiveWordsSkill | None = None


async def check_sensitive_words(text: str) -> bool:
    """向后兼容的 async 入口：返回 True 表示命中敏感词。"""
    global _sensitive_words_singleton
    if _sensitive_words_singleton is None:
        _sensitive_words_singleton = SensitiveWordsSkill()
    res = _sensitive_words_singleton.run("http-session", text)
    return res.blocked