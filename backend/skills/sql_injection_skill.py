"""SqlInjectionSkill —— Mid-Hook：检测 LLM 生成 SQL 中的注入风险，拦截危险语句。

职责：在 LLM 输出完成、调用工具 / 执行 SQL 之前执行。
红线对齐：严禁绕过权限直改数据库（12.1-2）；LLM 生成 SQL 需经注入检测（检查清单第 5 节）。
说明：本系统仅允许只读查询，写操作 SQL（INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE 等）一律阻断。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .security_log_skill import SecurityLogSkill


@dataclass
class SqlInjectionResult:
    blocked: bool
    reason: str
    sql_text: str
    meta: Dict[str, Any] = field(default_factory=dict)


# 危险写操作 / DDL 关键字（仅允许只读 SELECT/SHOW/DESCRIBE/EXPLAIN）
_WRITE_STATEMENT_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|MERGE|CALL|EXEC|EXECUTE|LOAD|SET|LOCK|RENAME)\b",
    re.IGNORECASE,
)
# 常见 SQL 注入特征
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in (
        r"(;|--|/\*).*(drop|delete|truncate|alter)\s",  # 堆叠/注释后跟危险操作
        r"\bunion\s+.*\bselect\b",  # 联合查询注入
        r"\bor\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",  # ' or 1=1
        r"\bwaitfor\s+delay\b",
        r"\bbenchmark\s*\(",
        r"\bsleep\s*\(",
        r"0x[0-9a-f]{8,}",  # 长十六进制字面量
        r"'\s*or\s*'1'\s*=\s*'1",
    )
]


class SqlInjectionSkill:
    """检测 SQL 注入风险并拦截非只读语句。"""

    def __init__(self, enable: bool = True, allow_write: bool = False):
        self.enable = enable
        # 系统强制只读；allow_write 仅用于测试，生产禁止开启。
        self.allow_write = allow_write

    def run(self, session_id: str, sql_text: str) -> SqlInjectionResult:
        if not self.enable:
            return SqlInjectionResult(
                blocked=False,
                reason="skill disabled",
                sql_text=sql_text,
                meta={},
            )

        text = (sql_text or "").strip()
        blocked = False
        reasons: List[str] = []

        # 1) 非只读语句拦截（核心红线：仅允许只读查询）
        if not self.allow_write:
            match = _WRITE_STATEMENT_RE.search(text)
            if match:
                blocked = True
                reasons.append(f"检测到非只读/危险 SQL 关键字: {match.group(1).upper()}")

        # 2) 注入特征检测
        for pattern in _INJECTION_PATTERNS:
            m = pattern.search(text)
            if m:
                blocked = True
                reasons.append(f"命中 SQL 注入特征: {m.group(0)!r}")
                break

        reason = "; ".join(reasons)
        meta = {"matched_reasons": reasons}

        SecurityLogSkill.log_security_event(
            event_type="SQL_INJECTION_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"sql_preview": text[:300], "matched_reasons": reasons},
        )

        return SqlInjectionResult(
            blocked=blocked,
            reason=reason,
            sql_text=sql_text,
            meta=meta,
        )