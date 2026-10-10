"""HookManager —— 三层 Hook 统一调度器（Pre / Mid / Post）。

架构（docs/security/安全注入防护Skill设计附录.md 1.1）：
用户输入 → Pre-Hook(输入安全校验) → LLM推理 → Mid-Hook(安全校验+业务质量校验)
        → 工具/SQL执行 → Post-Hook(结果校验/审计) → 返回前端

统一约束：
1. 每个 Skill 独立类，支持 enable 开关。
2. 各 Skill 独立返回结构体，经适配器转为统一 HookResult。
3. 任意 Hook 返回 blocked=True，链路立刻终止，写入安全审计日志。
4. Skill 内部 run 为同步代码；适配器用 asyncio.to_thread 包装，不阻塞事件循环。
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .prompt_injection_skill import PromptInjectionSkill
from .sql_injection_skill import SqlInjectionSkill
from .sql_result_check_skill import SqlResultCheckSkill
from .json_schema_skill import JsonSchemaCheckSkill
from .tool_param_check_skill import ToolParamCheckSkill
from .security_log_skill import SecurityLogSkill


# ====================== 统一返回结构体 ======================
@dataclass
class HookResult:
    blocked: bool
    reason: str
    payload: Any
    meta: Dict[str, Any] = field(default_factory=dict)


# 各阶段 Hook 的函数签名（async，返回统一 HookResult）
PreHookFn = Callable[[str, str], Awaitable[HookResult]]
MidHookFn = Callable[[str, str, Optional[Dict[str, Any]]], Awaitable[HookResult]]
PostHookFn = Callable[[str, Any], Awaitable[HookResult]]


class HookManager:
    """统一调度 Pre / Mid / Post 三层 Hook。

    灰度策略（设计附录第 11 节）：
    - `enforce=False`（默认告警模式）：命中只记审计日志与告警，不阻断主链路，
      用于上线初期统计误判率。
    - `enforce=True`（硬阻断模式）：命中即返回 blocked=True，链路终止。
    - 默认值由环境变量 `AGENT_HOOK_ENFORCE` 决定（"true" 才开启硬阻断）。
    """

    def __init__(self, enforce: Optional[bool] = None) -> None:
        if enforce is None:
            enforce = os.getenv("AGENT_HOOK_ENFORCE", "false").lower() == "true"
        self.enforce = enforce
        self.pre_hooks: List[PreHookFn] = []
        self.mid_hooks: List[MidHookFn] = []
        self.post_hooks: List[PostHookFn] = []

    def register_pre_hook(self, hook_func: PreHookFn) -> None:
        """注册 Pre-Hook：用户输入进入 LLM 之前执行。"""
        self.pre_hooks.append(hook_func)

    def register_mid_hook(self, hook_func: MidHookFn) -> None:
        """注册 Mid-Hook：LLM 输出后、工具/SQL 执行前。"""
        self.mid_hooks.append(hook_func)

    def register_post_hook(self, hook_func: PostHookFn) -> None:
        """注册 Post-Hook：SQL/工具执行完成，拿到返回结果之后。"""
        self.post_hooks.append(hook_func)

    def _apply_enforcement(self, stage: str, session_id: str, res: HookResult) -> HookResult:
        """按 enforce 开关决定是否真正阻断。

        告警模式下命中不阻断，但会：
        1. 在结果 meta 上标记 shadow_hit，供上层记录/观测；
        2. 写一条告警级审计日志，便于统计误判率。
        """
        if self.enforce or not res.blocked:
            return res
        res.meta = {**(res.meta or {}), "shadow_hit": True, "stage": stage}
        SecurityLogSkill.log_security_event(
            event_type=f"HOOK_SHADOW_HIT_{stage.upper()}",
            session_id=session_id,
            blocked=False,
            reason=f"[告警模式] {res.reason}",
            payload={"stage": stage, "meta": res.meta},
        )
        return HookResult(blocked=False, reason=res.reason, payload=res.payload, meta=res.meta)

    async def run_pre_hooks(self, session_id: str, user_query: str) -> Optional[HookResult]:
        """执行 Pre 阶段所有 Hook，遇到 blocked 直接返回。"""
        for hook in self.pre_hooks:
            res: HookResult = await hook(session_id, user_query)
            if res.blocked:
                return self._apply_enforcement("pre", session_id, res)
        return None

    async def run_mid_hooks(
        self,
        session_id: str,
        llm_raw_output: str,
        tool_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[HookResult]:
        """Mid 阶段：LLM 输出完成，准备调用工具/执行 SQL。"""
        for hook in self.mid_hooks:
            res: HookResult = await hook(session_id, llm_raw_output, tool_params)
            if res.blocked:
                return self._apply_enforcement("mid", session_id, res)
        return None

    async def run_post_hooks(self, session_id: str, result_data: Any) -> Optional[HookResult]:
        """Post 阶段：工具/SQL 执行完毕，拿到数据集，结果校验、脱敏审计。"""
        for hook in self.post_hooks:
            res: HookResult = await hook(session_id, result_data)
            if res.blocked:
                return self._apply_enforcement("post", session_id, res)
        return None


# ====================== 【适配器包装层】 ======================
# 将各个 Skill 的 run 方法包装成 HookManager 需要的统一 HookResult 格式，
# 隔离各 Skill 自定义 dataclass，统一出入参，不改动原有 Skill 业务代码。


async def pre_hook_prompt_injection(session_id: str, user_query: str) -> HookResult:
    skill = PromptInjectionSkill()
    skill_res = await asyncio.to_thread(skill.run, session_id, user_query)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_input,
        meta=skill_res.meta,
    )


async def mid_hook_sql_injection(
    session_id: str, llm_raw_output: str, tool_params: Optional[Dict[str, Any]]
) -> HookResult:
    skill = SqlInjectionSkill()
    # SQL 检测对象优先取 tool_params 中的 sql 字段，否则回退到 LLM 原始输出。
    sql_text = ""
    if tool_params and isinstance(tool_params.get("sql"), str):
        sql_text = tool_params["sql"]
    elif llm_raw_output:
        sql_text = llm_raw_output
    skill_res = await asyncio.to_thread(skill.run, session_id, sql_text)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=sql_text,
        meta=skill_res.meta,
    )


# 匹配 markdown 代码围栏（``` ... ``` 或 ```json ... ```）
_JSON_FENCE_RE = re.compile(r"```(?:json)?", re.IGNORECASE)

# 默认 JSON Schema（示例）。业务实例化时可按需替换。
_DEFAULT_TOOL_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query_type": {"type": "string"},
        "metric": {"type": "string"},
    },
    "required": ["query_type"],
}


async def mid_hook_json_schema(
    session_id: str, llm_raw_output: str, tool_params: Optional[Dict[str, Any]]
) -> HookResult:
    """P0：JSON Schema 校验 Skill 包装（Mid Hook）。

    仅在 LLM 输出**看起来像结构化 JSON**时才校验（```json 代码块，或首字符为 { / [）。
    纯文本 / 纯 SQL 输出并无 JSON 结构，跳过校验，避免误阻断非结构化返回。
    """
    text = (llm_raw_output or "").strip()
    if not text:
        return HookResult(blocked=False, reason="empty llm output, skip", payload=llm_raw_output, meta={})

    looks_like_json = (
        "```json" in text.lower()
        or _JSON_FENCE_RE.search(text) is not None
        or text.lstrip().startswith(("{", "["))
    )
    if not looks_like_json:
        return HookResult(blocked=False, reason="non-json output, skip", payload=llm_raw_output, meta={})

    schema = (tool_params or {}).get("schema") or _DEFAULT_TOOL_OUTPUT_SCHEMA
    skill = JsonSchemaCheckSkill(schema=schema)
    skill_res = await asyncio.to_thread(skill.run, session_id, llm_raw_output)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_text,
        meta=skill_res.meta,
    )


# 默认工具入参模型（示例），业务可覆盖。
class _DefaultQueryParam(BaseModel):
    query_type: str
    start_date: Optional[str] = Field(default=None, min_length=8)
    end_date: Optional[str] = None
    region: Optional[str] = None


async def mid_hook_tool_param_check(
    session_id: str, llm_raw_output: str, tool_params: Optional[Dict[str, Any]]
) -> HookResult:
    """P0：工具参数校验 Skill 包装（Mid Hook）。"""
    if tool_params is None:
        return HookResult(blocked=False, reason="no tool params, skip", payload=None, meta={})
    # 纯 SQL 查询走 SqlInjectionSkill + SqlResultCheckSkill，业务参数模型无适配场景，
    # 否则会被默认模型的必填字段误判为「参数缺失」。
    if "sql" in tool_params and "param_model" not in tool_params:
        pool = {k: v for k, v in tool_params.items() if k not in {"sql", "schema", "param_model"}}
        if not pool:
            return HookResult(blocked=False, reason="sql-only tool call, skip param model", payload=tool_params, meta={})
    # 业务可通过 tool_params["param_model"] 注入自定义 Pydantic 模型。
    model = (tool_params or {}).get("param_model") or _DefaultQueryParam
    skill = ToolParamCheckSkill(param_model=model)
    # 校验时剔除控制字段，避免污染真实入参。
    check_params = {k: v for k, v in tool_params.items() if k not in {"param_model", "schema", "sql"}}
    skill_res = await asyncio.to_thread(skill.run, session_id, check_params)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_params,
        meta=skill_res.meta,
    )


async def post_hook_sql_result_check(session_id: str, result_data: Any) -> HookResult:
    """P0：SQL 结果校验 Skill 包装（Post Hook）。"""
    skill = SqlResultCheckSkill()
    skill_res = await asyncio.to_thread(skill.run, session_id, result_data)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_data,
        meta=skill_res.meta,
    )


# ====================== 【工厂函数：快速初始化完整 Hook 管理器】 ======================
def create_hook_manager(enforce: Optional[bool] = None) -> HookManager:
    """一次性注册所有线上启用 Hook，开启/关闭 Skill 不侵入业务主流程。

    :param enforce: True=硬阻断，False=告警模式，None=读取环境变量 AGENT_HOOK_ENFORCE。
    """
    hm = HookManager(enforce=enforce)

    # Pre Hook
    hm.register_pre_hook(pre_hook_prompt_injection)

    # Mid Hook 顺序：安全 SQL 注入校验 → JSON Schema 校验 → 工具参数校验
    hm.register_mid_hook(mid_hook_sql_injection)
    hm.register_mid_hook(mid_hook_json_schema)
    hm.register_mid_hook(mid_hook_tool_param_check)

    # Post Hook
    hm.register_post_hook(post_hook_sql_result_check)

    return hm


# 进程级单例：避免每个请求重复构建 Hook 链路。
_hook_manager_singleton: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """获取进程级共享的 HookManager（懒加载单例）。"""
    global _hook_manager_singleton
    if _hook_manager_singleton is None:
        _hook_manager_singleton = create_hook_manager()
    return _hook_manager_singleton


async def run_input_hooks(session_id: str, user_query: str) -> Optional[HookResult]:
    """接入用便捷入口：执行 Pre-Hook 输入安全校验。

    返回 None 表示放行；返回 HookResult 且 blocked=True 表示应拒绝本次请求。
    （告警模式下 blocked 恒为 False，但 meta 中会带 shadow_hit 标记。）
    """
    return await get_hook_manager().run_pre_hooks(session_id, user_query)


async def run_mid_hooks(
    session_id: str,
    llm_raw_output: str,
    tool_params: Optional[Dict[str, Any]] = None,
) -> Optional[HookResult]:
    """接入用便捷入口：执行 Mid-Hook（工具/SQL 调用前安全与参数校验）。

    返回 None 表示全部放行；返回 HookResult 时看 blocked 决定是否终止本次工具调用。
    （告警模式下 blocked 恒为 False，但 meta 中会带 shadow_hit 标记。）
    """
    return await get_hook_manager().run_mid_hooks(session_id, llm_raw_output, tool_params)


async def run_post_hooks(session_id: str, result_data: Any) -> Optional[HookResult]:
    """接入用便捷入口：执行 Post-Hook（工具/SQL 结果校验与审计）。

    返回 None 表示无命中；返回 HookResult 时看 blocked 决定是否丢弃本次工具结果。
    """
    return await get_hook_manager().run_post_hooks(session_id, result_data)