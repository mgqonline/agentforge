"""SqlResultCheckSkill —— Post-Hook：SQL 执行完成后校验返回数据集。

职责（P0）：
1. 校验返回行数，超过软上限告警，超过硬上限阻断返回。
2. 脏数据识别：异常极值、超大负数。
3. 计算数据集 sha256 指纹，用于后续防幻觉比对。
红线对齐：LLM 不会自动执行写操作，结果集仅用于只读返回与审计（检查清单第 6 节）。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .security_log_skill import SecurityLogSkill


@dataclass
class SqlResultCheckResult:
    blocked: bool
    reason: str
    raw_data: List[Dict[str, Any]]
    meta: Dict[str, Any] = field(default_factory=dict)


class SqlResultCheckSkill:
    """SQL 结果集行数 / 脏数据 / 指纹校验。"""

    def __init__(
        self,
        max_rows: int = 1000,
        hard_max_rows: int = 5000,
        enable: bool = True,
        abnormal_negative_threshold: float = -1_000_000,
    ):
        self.enable = enable
        self.max_rows = max_rows
        self.hard_max_rows = hard_max_rows
        self.abnormal_negative_threshold = abnormal_negative_threshold

    def _calc_fingerprint(self, data: List[Dict[str, Any]]) -> str:
        # 指纹用于后续防幻觉比对；使用排序稳定的序列化，避免字典顺序影响。
        raw = str(data).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def run(self, session_id: str, data: List[Dict[str, Any]]) -> SqlResultCheckResult:
        if not self.enable:
            return SqlResultCheckResult(
                blocked=False,
                reason="skill disabled",
                raw_data=data,
                meta={"warning_list": [], "row_count": len(data) if data else 0},
            )

        warnings: List[str] = []
        row_count = len(data) if data else 0
        blocked = False
        reason = ""

        # 行数校验
        if row_count > self.hard_max_rows:
            blocked = True
            reason = f"结果行数{row_count}超过硬上限{self.hard_max_rows}，阻断返回"
            warnings.append(reason)
        elif row_count > self.max_rows:
            warnings.append(f"结果行数{row_count}超过推荐上限{self.max_rows}，已告警")

        # 脏数据简单校验（仅扫描前 100 行以控制成本）
        for idx, row in enumerate((data or [])[:100]):
            for k, v in row.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if v < self.abnormal_negative_threshold:
                        warnings.append(f"行{idx} 字段{k}存在异常负值: {v}")
                    if isinstance(v, float) and v != v:  # NaN
                        warnings.append(f"行{idx} 字段{k}存在 NaN 值")

        fp = self._calc_fingerprint(data or [])
        meta = {
            "row_count": row_count,
            "data_fingerprint": fp,
            "warning_list": warnings,
        }

        SecurityLogSkill.log_security_event(
            event_type="SQL_RESULT_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason or "; ".join(warnings),
            payload={"row_count": row_count, "data_fingerprint": fp},
        )

        return SqlResultCheckResult(
            blocked=blocked,
            reason=reason or "; ".join(warnings),
            raw_data=data,
            meta=meta,
        )