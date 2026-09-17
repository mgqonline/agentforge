import re
from dataclasses import dataclass
from typing import Any


WRITE_INTENT_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|replace|grant|revoke|merge|call)\b"
    r"|新增|插入|修改|更新|删除|删掉|清空|建表|创建表|改表|授权|撤销|发送|导出|外部调用",
    re.IGNORECASE,
)


SIDE_EFFECT_PATTERN = re.compile(
    r"删除|删掉|清空|修改|更新|新增|插入|创建|建表|改表|发送|导出|调用外部|执行|落库|写入",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool = False
    approval_kind: str = ""
    risk_level: str = "low"
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "approval_kind": self.approval_kind,
            "risk_level": self.risk_level,
            "reason": self.reason,
        }


def evaluate_tool_policy(tool_name: str, arguments: Any, user_permissions: set[str] | None = None) -> PolicyDecision:
    permissions = user_permissions or set()
    if tool_name == "query_sql_database":
        query = ""
        if isinstance(arguments, dict):
            query = str(arguments.get("query") or "")
        else:
            query = str(arguments or "")
        if WRITE_INTENT_PATTERN.search(query):
            return PolicyDecision(
                allowed=False,
                risk_level="critical",
                reason="write or schema-changing database operations are not allowed",
            )
        return PolicyDecision(allowed="tool:read" in permissions, risk_level="medium", reason="readonly sql")

    if tool_name == "search_knowledge_base":
        return PolicyDecision(allowed="tool:read" in permissions, risk_level="low", reason="readonly knowledge search")

    return PolicyDecision(allowed=False, risk_level="high", reason=f"unknown tool: {tool_name}")


def evaluate_task_policy(task: str, mode: str, user_permissions: set[str] | None = None) -> PolicyDecision:
    if mode != "orchestrator":
        return PolicyDecision(allowed=True, risk_level="low", reason="non-orchestrator analysis")
    if SIDE_EFFECT_PATTERN.search(task or ""):
        return PolicyDecision(
            allowed=True,
            requires_approval=True,
            approval_kind="side_effect",
            risk_level="high",
            reason="task appears to request side-effect execution",
        )
    return PolicyDecision(allowed=True, risk_level="medium", reason="orchestrator task")


def evaluate_approval_decision(user_permissions: set[str]) -> PolicyDecision:
    if "approval:decide" not in user_permissions:
        return PolicyDecision(allowed=False, risk_level="high", reason="user lacks approval decision permission")
    return PolicyDecision(allowed=True, risk_level="medium", reason="approval decision permitted")
