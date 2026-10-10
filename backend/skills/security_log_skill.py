"""SecurityLogSkill —— 统一安全事件审计日志。

职责：记录所有 Skill 校验事件，session_id 全链路追踪，用于审计、溯源。
红线对齐：安全事件、拦截事件需完整审计日志（见 docs/security/安全检查清单.md 第 4 节）。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

# 独立的安全审计 logger，命名空间隔离，便于生产环境单独配置 sink（文件/ELK）。
security_logger = logging.getLogger("agentforge.security")

# 仅在未配置任何 handler 时挂一个 StreamHandler，避免业务代码重复打印。
if not security_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [SECURITY] %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    security_logger.addHandler(_handler)
    security_logger.setLevel(os.getenv("AGENT_SECURITY_LOG_LEVEL", "INFO").upper())
    security_logger.propagate = False


class SecurityLogSkill:
    """统一安全事件日志写入（静态工具，无状态）。"""

    @staticmethod
    def log_security_event(
        event_type: str,
        session_id: str,
        blocked: bool,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """写入一条安全审计日志，携带 session_id 链路追踪。

        日志不记录用户隐私明文；payload 仅传入业务脱敏后的字段。
        """
        level = logging.ERROR if blocked else logging.INFO
        record = {
            "event_type": event_type,
            "session_id": session_id,
            "blocked": bool(blocked),
            "reason": reason,
            "payload": payload or {},
        }
        try:
            serialized = json.dumps(record, ensure_ascii=False, default=str)
        except Exception:
            serialized = repr(record)
        security_logger.log(level, serialized)