# 安全注入防护Skill设计附录.md

文档版本：v1.0


适用模块：backend/skills 整套Skill体系

## 目录

1. 总体架构说明

2. 原有安全Skill设计（Prompt注入、SQL注入、安全日志）

3. v1.0 新增P0 Skill设计（SQL结果校验、JSON Schema校验、工具入参校验）

4. HookManager 统一调度器设计

5. 项目目录结构 __init__.py

6. 完整源码

7. 单元测试代码

8. 业务调用示例

9. 依赖清单

10. CI测试闭环方案

11. 上线灰度策略

12. 系统强制安全红线（不可突破）

## 1. 总体架构说明

### 1.1 三层Hook链路

用户输入 → Pre-Hook（输入安全校验） → LLM推理 → Mid-Hook（安全校验 + 业务质量校验） → 工具/SQL执行 → Post-Hook（结果校验、审计） → 返回前端

- Pre-Hook：用户原始输入进入LLM前执行

- Mid-Hook：LLM输出完成，调用工具/执行SQL之前执行

- Post-Hook：SQL/工具执行完毕，拿到数据集之后执行

### 1.2 统一约束

1. 所有Skill独立类，支持enable开关，可单独启用/关闭，不侵入业务主逻辑。

2. 每个Skill拥有独立返回结构体，通过适配器转为统一`HookResult`。

3. 任意Hook返回`blocked=True`，链路立刻终止，写入安全审计日志。

4. 全部Skill配套单元测试，纳入CI流水线，实现测试闭环。

5. Skill内部run方法为同步代码；在Hook适配器中使用`asyncio.to_thread`包装，不阻塞async事件循环。

### 1.3 HookResult 统一返回模型

```Plain Text
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class HookResult:
    blocked: bool
    reason: str
    payload: Any
    meta: Dict[str, Any]

```

## 2. 原有安全Skill设计

### 2.1 PromptInjectionSkill Pre-Hook

职责：检测用户输入提示词注入、越狱指令，阻断恶意prompt。

输出结构体：

```Plain Text
@dataclass
class PromptInjectionResult:
    blocked: bool
    reason: str
    raw_input: str
    meta: Dict[str, Any]

```

### 2.2 SqlInjectionSkill Mid-Hook

职责：检测LLM生成SQL中的注入风险，拦截危险SQL语句。

输出结构体：

```Plain Text
@dataclass
class SqlInjectionResult:
    blocked: bool
    reason: str
    sql_text: str
    meta: Dict[str, Any]

```

### 2.3 SecurityLogSkill 全局日志埋点

职责：统一记录所有Skill校验事件，session_id全链路追踪，用于审计、溯源。

```Plain Text
class SecurityLogSkill:
    @staticmethod
    def log_security_event(event_type: str, session_id: str, blocked: bool, reason: str, payload: dict):
        """统一安全事件日志写入"""
        pass

```

## 3. v1.0 新增P0 Skill设计

P0优先级，优先上线，业务质量校验，和安全Skill并行执行

### 3.1 SqlResultCheckSkill Post-Hook

**位置**：SQL执行完成后

**能力**

1. 校验返回行数，超过软上限告警，超过硬上限阻断返回。

2. 脏数据识别：异常极值、超大负数。

3. 计算数据集sha256指纹，用于后续防幻觉比对。

**返回结构体**

```Plain Text
@dataclass
class SqlResultCheckResult:
    blocked: bool
    reason: str
    raw_data: List[Dict[str, Any]]
    meta: Dict[str, Any]

```

meta字段：`row_count`、`data_fingerprint`、`warning_list`

### 3.2 JsonSchemaCheckSkill Mid-Hook

**位置**：LLM输出结构化JSON之后，工具调用之前

**能力**

1. 自动剥离markdown ````json`代码块标记。

2. JSON解析 + jsonschema强校验（必填字段、类型、枚举）。

3. 无法修复的JSON格式错误直接阻断。

**返回结构体**

```Plain Text
@dataclass
class JsonSchemaCheckResult:
    blocked: bool
    reason: str
    raw_text: str
    parsed_json: Optional[Dict[str, Any]]
    meta: Dict[str, Any]

```

### 3.3 ToolParamCheckSkill Mid-Hook

**位置**：Agent调用任意工具前

**能力**

1. 基于Pydantic模型做参数强校验。

2. 自动清洗字符串首尾空格。

3. 校验：必填项、字符串长度、数值范围、枚举。

4. 参数非法返回结构化错误信息，支持Agent重试。

**返回结构体**

```Plain Text
@dataclass
class ToolParamCheckResult:
    blocked: bool
    reason: str
    raw_params: Dict[str, Any]
    meta: Dict[str, Any]

```

## 4. HookManager 统一调度器设计

文件路径：`backend/skills/hook_manager.py`

```Plain Text
from dataclasses import dataclass
from typing import Callable, List, Optional, Any, Dict, Union
import asyncio

# 统一返回结构体
@dataclass
class HookResult:
    blocked: bool
    reason: str
    payload: Any
    meta: Dict[str, Any]


class HookManager:
    def __init__(self):
        # 三层Hook链路：Pre / Mid / Post
        self.pre_hooks: List[Callable] = []
        self.mid_hooks: List[Callable] = []
        self.post_hooks: List[Callable] = []

    def register_pre_hook(self, hook_func: Callable):
        """注册 Pre-Hook：用户输入进入LLM之前执行"""
        self.pre_hooks.append(hook_func)

    def register_mid_hook(self, hook_func: Callable):
        """注册 Mid-Hook：LLM输出后、工具/SQL执行前"""
        self.mid_hooks.append(hook_func)

    def register_post_hook(self, hook_func: Callable):
        """注册 Post-Hook：SQL/工具执行完成，拿到返回结果之后"""
        self.post_hooks.append(hook_func)

    async def run_pre_hooks(self, session_id: str, user_query: str) -> Optional[HookResult]:
        """执行Pre阶段所有Hook，遇到blocked直接返回"""
        for hook in self.pre_hooks:
            res: HookResult = await hook(session_id, user_query)
            if res.blocked:
                return res
        return None

    async def run_mid_hooks(
            self,
            session_id: str,
            llm_raw_output: str,
            tool_params: Optional[Dict[str, Any]] = None
    ) -> Optional[HookResult]:
        """Mid阶段：LLM输出完成，准备调用工具/执行SQL"""
        for hook in self.mid_hooks:
            res: HookResult = await hook(session_id, llm_raw_output, tool_params)
            if res.blocked:
                return res
        return None

    async def run_post_hooks(self, session_id: str, result_data: Any) -> Optional[HookResult]:
        """Post阶段：工具/SQL执行完毕，拿到数据集，结果校验、脱敏审计"""
        for hook in self.post_hooks:
            res: HookResult = await hook(session_id, result_data)
            if res.blocked:
                return res
        return None


# ====================== 【适配器包装层】======================
# 将各个Skill的run方法包装成HookManager需要的统一HookResult格式
# 作用：隔离各个Skill自定义dataclass，统一出入参，不需要改动原有Skill业务代码

from .prompt_injection_skill import PromptInjectionSkill
from .sql_injection_skill import SqlInjectionSkill
from .sql_result_check_skill import SqlResultCheckSkill
from .json_schema_skill import JsonSchemaCheckSkill
from .tool_param_check_skill import ToolParamCheckSkill
from .security_log_skill import SecurityLogSkill


async def pre_hook_prompt_injection(session_id: str, user_query: str) -> HookResult:
    skill = PromptInjectionSkill()
    skill_res = await asyncio.to_thread(skill.run, session_id, user_query)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_input,
        meta=skill_res.meta
    )


async def mid_hook_sql_injection(session_id: str, llm_raw_output: str, tool_params: Dict[str, Any]) -> HookResult:
    skill = SqlInjectionSkill()
    skill_res = await asyncio.to_thread(skill.run, session_id, llm_raw_output)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=llm_raw_output,
        meta=skill_res.meta
    )


async def mid_hook_json_schema(session_id: str, llm_raw_output: str, tool_params: Dict[str, Any]) -> HookResult:
    """P0：JSON Schema校验Skill包装（Mid Hook）"""
    # 业务实例化时注入schema，示例schema
    schema = {
        "type": "object",
        "properties": {
            "query_type": {"type": "string"},
            "metric": {"type": "string"}
        },
        "required": ["query_type"]
    }
    skill = JsonSchemaCheckSkill(schema=schema)
    skill_res = await asyncio.to_thread(skill.run, session_id, llm_raw_output)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_text,
        meta=skill_res.meta
    )


async def mid_hook_tool_param_check(session_id: str, llm_raw_output: str, tool_params: Dict[str, Any]) -> HookResult:
    """P0：工具参数校验Skill包装（Mid Hook）"""
    from pydantic import BaseModel, Field
    class QueryParam(BaseModel):
        start_date: str = Field(min_length=8)
        end_date: str
        region: str
    skill = ToolParamCheckSkill(param_model=QueryParam)
    skill_res = await asyncio.to_thread(skill.run, session_id, tool_params)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_params,
        meta=skill_res.meta
    )


async def post_hook_sql_result_check(session_id: str, result_data: Any) -> HookResult:
    """P0：SQL结果校验Skill包装（Post Hook）"""
    skill = SqlResultCheckSkill()
    skill_res = await asyncio.to_thread(skill.run, session_id, result_data)
    return HookResult(
        blocked=skill_res.blocked,
        reason=skill_res.reason,
        payload=skill_res.raw_data,
        meta=skill_res.meta
    )


# ====================== 【工厂函数：快速初始化完整Hook管理器】 ======================
def create_hook_manager() -> HookManager:
    """
    工厂方法：一次性注册所有线上启用Hook
    在这里开启/关闭Skill，不需要修改业务主流程
    """
    hm = HookManager()

    # Pre Hook
    hm.register_pre_hook(pre_hook_prompt_injection)

    # Mid Hook 顺序：安全SQL注入校验 → JSON校验 → 工具参数校验
    hm.register_mid_hook(mid_hook_sql_injection)
    hm.register_mid_hook(mid_hook_json_schema)
    hm.register_mid_hook(mid_hook_tool_param_check)

    # Post Hook
    hm.register_post_hook(post_hook_sql_result_check)

    return hm

```

## 5. 项目目录结构 & __init__.py

### 目录

```Plain Text
backend/
└── skills/
    ├── __init__.py
    ├── hook_manager.py
    ├── prompt_injection_skill.py
    ├── sql_injection_skill.py
    ├── security_log_skill.py
    ├── sql_result_check_skill.py
    ├── json_schema_skill.py
    └── tool_param_check_skill.py

```

### backend/skills/__init__.py

```Plain Text
# backend/skills/__init__.py
"""
T3 Project Skills Package v1.0
Exports all skill classes, result dataclasses and HookManager
"""

# Hook Manager & HookResult
from .hook_manager import HookManager, HookResult, create_hook_manager

# Original Security Skills
from .prompt_injection_skill import PromptInjectionSkill
from .sql_injection_skill import SqlInjectionSkill
from .security_log_skill import SecurityLogSkill

# v1.0 P0 New Skills
from .sql_result_check_skill import SqlResultCheckSkill, SqlResultCheckResult
from .json_schema_skill import JsonSchemaCheckSkill, JsonSchemaCheckResult
from .tool_param_check_skill import ToolParamCheckSkill, ToolParamCheckResult

__all__ = [
    # Hook
    "HookManager",
    "HookResult",
    "create_hook_manager",

    # Security
    "PromptInjectionSkill",
    "SqlInjectionSkill",
    "SecurityLogSkill",

    # P0 v1.0
    "SqlResultCheckSkill",
    "SqlResultCheckResult",
    "JsonSchemaCheckSkill",
    "JsonSchemaCheckResult",
    "ToolParamCheckSkill",
    "ToolParamCheckResult",
]

```

## 6. v1.0 新增Skill完整源码

### 6.1 sql_result_check_skill.py

```Plain Text
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import hashlib

from .security_log_skill import SecurityLogSkill

@dataclass
class SqlResultCheckResult:
    blocked: bool
    reason: str
    raw_data: List[Dict[str, Any]]
    meta: Dict[str, Any]

class SqlResultCheckSkill:
    def __init__(
        self,
        max_rows: int = 1000,
        hard_max_rows: int = 5000,
        enable: bool = True
    ):
        self.enable = enable
        self.max_rows = max_rows
        self.hard_max_rows = hard_max_rows

    def _calc_fingerprint(self, data: List[Dict[str, Any]]) -> str:
        raw = str(data).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def run(self, session_id: str, data: List[Dict[str, Any]]) -> SqlResultCheckResult:
        if not self.enable:
            return SqlResultCheckResult(
                blocked=False,
                reason="skill disabled",
                raw_data=data,
                meta={"warning_list": [], "row_count": len(data)}
            )

        warnings: List[str] = []
        row_count = len(data)
        blocked = False
        reason = ""

        # 行数校验
        if row_count > self.hard_max_rows:
            blocked = True
            reason = f"结果行数{row_count}超过硬上限{self.hard_max_rows}，阻断返回"
            warnings.append(reason)
        elif row_count > self.max_rows:
            warnings.append(f"结果行数{row_count}超过推荐上限{self.max_rows}，已告警")

        # 脏数据简单校验
        for idx, row in enumerate(data[:100]):
            for k, v in row.items():
                if isinstance(v, (int, float)) and v < -1000000:
                    warnings.append(f"行{idx} 字段{k}存在异常负值: {v}")

        fp = self._calc_fingerprint(data)
        meta = {
            "row_count": row_count,
            "data_fingerprint": fp,
            "warning_list": warnings
        }

        SecurityLogSkill.log_security_event(
            event_type="SQL_RESULT_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason or "; ".join(warnings),
            payload={"row_count": row_count}
        )

        return SqlResultCheckResult(
            blocked=blocked,
            reason=reason or "; ".join(warnings),
            raw_data=data,
            meta=meta
        )

```

### 6.2 json_schema_skill.py

```Plain Text
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import re
from jsonschema import validate, ValidationError

from .security_log_skill import SecurityLogSkill

@dataclass
class JsonSchemaCheckResult:
    blocked: bool
    reason: str
    raw_text: str
    parsed_json: Optional[Dict[str, Any]]
    meta: Dict[str, Any]

class JsonSchemaCheckSkill:
    def __init__(self, schema: Dict[str, Any], enable: bool = True):
        self.enable = enable
        self.schema = schema
        self.code_block_re = re.compile(r"```(json)?n?(.*?)n?```", re.S)

    def _extract_json(self, text: str) -> str:
        match = self.code_block_re.search(text)
        if match:
            return match.group(2).strip()
        return text.strip()

    def run(self, session_id: str, raw_text: str) -> JsonSchemaCheckResult:
        if not self.enable:
            return JsonSchemaCheckResult(
                blocked=False,
                reason="skill disabled",
                raw_text=raw_text,
                parsed_json=None,
                meta={}
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

        SecurityLogSkill.log_security_event(
            event_type="JSON_SCHEMA_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"raw_text_preview": raw_text[:200]}
        )

        return JsonSchemaCheckResult(
            blocked=blocked,
            reason=reason,
            raw_text=raw_text,
            parsed_json=parsed,
            meta=meta
        )

```

### 6.3 tool_param_check_skill.py

```Plain Text
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError

from .security_log_skill import SecurityLogSkill

@dataclass
class ToolParamCheckResult:
    blocked: bool
    reason: str
    raw_params: Dict[str, Any]
    meta: Dict[str, Any]

class ToolParamCheckSkill:
    def __init__(self, param_model: type[BaseModel], enable: bool = True):
        self.enable = enable
        self.param_model = param_model

    def run(self, session_id: str, raw_params: Dict[str, Any]) -> ToolParamCheckResult:
        if not self.enable:
            return ToolParamCheckResult(
                blocked=False,
                reason="skill disabled",
                raw_params=raw_params,
                meta={}
            )

        blocked = False
        reason = ""
        meta: Dict[str, Any] = {}

        try:
            # 自动清洗：字符串去首尾空格
            cleaned = {}
            for k, v in raw_params.items():
                if isinstance(v, str):
                    cleaned[k] = v.strip()
                else:
                    cleaned[k] = v
            self.param_model(**cleaned)
        except ValidationError as e:
            blocked = True
            reason = f"工具参数校验失败: {e.errors()}"
            meta["errors"] = e.errors()

        SecurityLogSkill.log_security_event(
            event_type="TOOL_PARAM_CHECK",
            session_id=session_id,
            blocked=blocked,
            reason=reason,
            payload={"raw_params": raw_params}
        )

        return ToolParamCheckResult(
            blocked=blocked,
            reason=reason,
            raw_params=raw_params,
            meta=meta
        )

```

## 7. pytest 单元测试文件 test_p0_skills.py

```Plain Text
import pytest
from pydantic import BaseModel, Field
from backend.skills.sql_result_check_skill import SqlResultCheckSkill
from backend.skills.json_schema_skill import JsonSchemaCheckSkill
from backend.skills.tool_param_check_skill import ToolParamCheckSkill

# ---------------------- SqlResultCheckSkill Test ----------------------
def test_sql_result_check_normal():
    skill = SqlResultCheckSkill(max_rows=100, hard_max_rows=500)
    res = skill.run("s1", [{"amount": 100}])
    assert res.blocked is False
    assert len(res.meta["warning_list"]) == 0

def test_sql_result_check_hard_limit():
    skill = SqlResultCheckSkill(max_rows=100, hard_max_rows=10)
    big_data = [{"a": i} for i in range(20)]
    res = skill.run("s2", big_data)
    assert res.blocked is True

def test_sql_result_check_abnormal_value():
    skill = SqlResultCheckSkill()
    data = [{"amount": -99999999}]
    res = skill.run("s3", data)
    assert any("异常负值" in w for w in res.meta["warning_list"])

# ---------------------- JsonSchemaCheckSkill Test ----------------------
test_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "number"}
    },
    "required": ["name"]
}

def test_json_schema_valid_plain():
    skill = JsonSchemaCheckSkill(test_schema)
    text = '{"name":"test","age":20}'
    res = skill.run("s4", text)
    assert res.blocked is False
    assert res.parsed_json["name"] == "test"

def test_json_schema_valid_markdown():
    skill = JsonSchemaCheckSkill(test_schema)
    text = "```jsonn{"name":"abc"}n```"
    res = skill.run("s5", text)
    assert res.blocked is False

def test_json_schema_missing_required():
    skill = JsonSchemaCheckSkill(test_schema)
    text = '{"age":30}'
    res = skill.run("s6", text)
    assert res.blocked is True

# ---------------------- ToolParamCheckSkill Test ----------------------
class QueryParam(BaseModel):
    start_date: str = Field(min_length=8)
    end_date: str
    region: str

def test_tool_param_valid():
    skill = ToolParamCheckSkill(QueryParam)
    params = {"start_date": "20260101", "end_date": "20260131", "region": "HN"}
    res = skill.run("s7", params)
    assert res.blocked is False

def test_tool_param_invalid():
    skill = ToolParamCheckSkill(QueryParam)
    params = {"start_date": "2026", "end_date": "20260131"}
    res = skill.run("s8", params)
    assert res.blocked is True

```

## 8. 业务调用示例（main.py）

```Plain Text
# main.py
from backend.skills import create_hook_manager

async def agent_session_flow(session_id: str, user_query: str):
    hook_mgr = create_hook_manager()

    # Pre Hook 输入校验
    pre_check = await hook_mgr.run_pre_hooks(session_id, user_query)
    if pre_check and pre_check.blocked:
        return {"code":403, "msg": pre_check.reason, "meta": pre_check.meta}

    # --- 此处执行业务LLM调用，拿到llm_raw_output，生成tool_params ---
    llm_raw_output = "..."
    tool_params = {}

    # Mid Hook
    mid_check = await hook_mgr.run_mid_hooks(session_id, llm_raw_output, tool_params)
    if mid_check and mid_check.blocked:
        return {"code":403, "msg": mid_check.reason, "meta": mid_check.meta}

    # --- 执行SQL / 工具调用，拿到sql_result_data ---
    sql_result_data = []

    # Post Hook
    post_check = await hook_mgr.run_post_hooks(session_id, sql_result_data)
    if post_check and post_check.blocked:
        return {"code":403, "msg": post_check.reason, "meta": post_check.meta}

    return {"code": 200, "data": sql_result_data}

```

## 9. 依赖清单

```Plain Text
pip install pydantic jsonschema pytest

```

## 10. CI测试闭环方案

1. 代码提交触发CI任务

2. 执行单元测试：`pytest tests/test_p0_skills.py -v`

3. 全部单元测试必须pass，否则阻断MR/代码合并

4. 上线初期：P0 Skill默认告警模式，硬阻断阈值调高，观测误判率

5. 持续沉淀业务样例，加入回归测试集

## 11. 上线灰度策略

1. v1.0只上线3个P0 Skill，和原有安全Skill并行。

2. 灰度开关：每个Skill独立enable开关，支持会话级别启停。

3. 上线初期：阻断阈值放宽，优先记录告警日志，统计误判率。

4. 指标观测：告警数量、误判案例、参数校验失败率；稳定后再开启强阻断。

5. 生产捕获的真实问题，自动加入回归测试用例库，持续闭环。

## 12. 系统强制安全红线（不可突破）

本章节为**不可突破的工程红线**，代码评审、MR合并、上线前必须逐项核验，违反则禁止合并、禁止发布、禁止上线，无任何特例豁免。适用于所有Skill、Agent业务代码、Hook调度逻辑、数据库操作、LLM交互逻辑。

### 12.1 五大强制安全禁令

1. **严禁提交密钥、证书或敏感数据**
禁止在代码、配置文件、静态资源、日志输出中硬编码密钥、数据库密码、AK/SK、Token、证书私钥、账号密码等敏感凭证。所有敏感配置统一通过环境变量、配置中心、密钥托管服务注入，Git仓库严禁留存任何敏感数据。

2. **严禁绕过权限直改数据库**
所有数据库读写操作必须前置身份认证、会话校验、数据权限校验。禁止跳过权限校验逻辑直接执行SQL、调用数据库接口；禁止硬编码超级权限、绕过拦截白名单执行数据操作。

3. **严禁无确认执行写操作**
系统所有数据库写操作（INSERT/UPDATE/DELETE/ALTER/DROP等变更、删除、修改类操作），必须具备强制校验、日志全量留存机制；高危写操作必须配置人工二次确认，禁止Agent、LLM自动触发、静默执行数据写变更。本系统仅允许只读查询，彻底禁止自动写操作。

4. **严禁通过提示注入改变白名单**
安全白名单、黑名单、拦截规则、Skill开关、权限策略、数据表访问策略均为**静态运维配置**。禁止用户Prompt、LLM输出、工具调用参数动态修改、绕过、覆盖安全规则，杜绝提示词注入篡改安全策略的风险。

5. **严禁核心功能用 Mock 冒充**
Mock数据、Mock接口、Mock逻辑仅允许用于本地开发、单元测试场景。**生产、测试环境严禁使用Mock替代核心业务、安全校验、数据库能力**，禁止依靠Mock通过测试、掩盖功能缺陷，保证上线功能真实可用。

### 12.2 MR/上线强制核验清单

代码合并、版本发布前必须全部满足，缺一不可：

- [√] 代码无任何硬编码敏感密钥、证书、账号密码

- [√] 所有数据库操作均经过权限与安全Hook校验，无绕过逻辑

- [√] 系统无自动写数据库逻辑，所有高危变更操作全部禁用

- [√] 安全规则、黑白名单不支持用户/LLM动态修改

- [√] 生产环境无Mock核心业务逻辑，无Mock逃逸风险

- [√] 所有Skill安全拦截、业务校验逻辑完整，单元测试全覆盖

### 12.3 违规处理规则

任意红线违规：阻断MR合并、阻断CI发布、回退版本，限期整改，纳入代码质量考核。

