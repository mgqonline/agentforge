"""AgentForge Skills Package v1.0 —— 三层 Hook 安全与业务质量校验 Skill 体系。

适用：backend 整套 Skill 体系（见 docs/security/安全注入防护Skill设计附录.md）。
导出所有 Skill 类、返回结构体与 HookManager 统一调度器。
"""

# Hook Manager & HookResult
from .hook_manager import HookManager, HookResult, create_hook_manager

# Original Security Skills
from .prompt_injection_skill import PromptInjectionSkill, PromptInjectionResult
from .sql_injection_skill import SqlInjectionSkill, SqlInjectionResult
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
    "PromptInjectionResult",
    "SqlInjectionSkill",
    "SqlInjectionResult",
    "SecurityLogSkill",
    # P0 v1.0
    "SqlResultCheckSkill",
    "SqlResultCheckResult",
    "JsonSchemaCheckSkill",
    "JsonSchemaCheckResult",
    "ToolParamCheckSkill",
    "ToolParamCheckResult",
]