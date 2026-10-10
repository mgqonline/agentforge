---
name: security_hook_guard
description: 当修改 backend/skills 下的安全 Skill、HookManager 调度链路、Pre/Mid/Post Hook 适配器，或涉及提示词注入、SQL 注入、工具入参校验、SQL 结果集校验、JSON Schema 校验与安全审计日志时，自动触发此技能。用于守护三层 Hook 安全链路与扫描五大安全红线。
---

# 安全注入防护 Hook 开发准则 (Security Hook Guard)

本技能定义 `agentforge` 后端 `backend/skills` 三层 Hook 安全链路的开发规范、威胁模型与必检清单。
权威来源：`docs/security/安全检查清单.md`、`docs/security/安全注入防护Skill设计附录.md`。

## 1. 三层 Hook 链路与统一约束

链路：用户输入 → **Pre-Hook** → LLM 推理 → **Mid-Hook** → 工具/SQL 执行 → **Post-Hook** → 返回前端

统一约束（修改时必须保持）：
1. 每个 Skill 为独立类，支持 `enable` 开关，不侵入业务主逻辑。
2. 每个 Skill 有独立返回结构体，经 `backend/skills/hook_manager.py` 的适配器转为统一 `HookResult`。
3. 任意 Hook 返回 `blocked=True`，链路立刻终止并写 `SecurityLogSkill` 审计日志。
4. Skill 内部 `run` 为**同步**代码；适配器用 `asyncio.to_thread` 包装，不阻塞 async 事件循环。
5. 全部 Skill 配套单元测试，纳入 CI（`tests/test_p0_skills.py`）。

## 2. 五大强制安全红线（不可突破）

1. **严禁提交密钥、证书或敏感数据** —— Skill/Hook 代码不出现硬编码凭证，日志不打印明文凭证。
2. **严禁绕过权限直改数据库** —— 所有库操作前置权限校验，无后门 SQL。
3. **严禁无确认执行写操作** —— 本系统**仅允许只读查询**；`SqlInjectionSkill` 必须拦截 INSERT/UPDATE/DELETE/ALTER/DROP 等。
4. **严禁通过提示注入改变白名单** —— 黑白名单、拦截规则、Skill 开关为**静态配置**；规则库不得被用户 Prompt / LLM 输出 / 工具参数动态改写。
5. **严禁核心功能用 Mock 冒充** —— 生产环境不得用 Mock 替代安全校验。

## 3. 变更开发步骤

1. **影响面评估先行**：修改任何 Skill / Hook 前运行 `gitnexus_impact({target: "符号名", direction: "upstream"})`，HIGH/CRITICAL 必须先告知用户。
2. **静态规则库补充**：新增危险模式时，在对应 Skill 的静态规则常量中补充（如 `_DEFAULT_INJECTION_PATTERNS`、`_WRITE_STATEMENT_RE`），禁止引入运行时可变入口。
3. **适配器契约对齐**：新增 Skill 需在 `hook_manager.py` 增加 async 适配器，并在 `create_hook_manager()` 中按阶段注册。
4. **测试闭环**：在 `tests/test_p0_skills.py` 增补用例，本地执行 `pytest tests/test_p0_skills.py -v` 全绿后提交。
5. **导出同步**：新增对外的 Skill 类 / 结果结构体，需在 `backend/skills/__init__.py` 的 `__all__` 中同步导出。

## 4. 错误响应标准格式

Hook 阻断时返回结构化结果，交由业务层转为受控响应（HTTP 403 风格）：

```json
{
  "blocked": true,
  "reason": "检测到非只读/危险 SQL 关键字: DELETE",
  "payload": "DELETE FROM users",
  "meta": {"matched_reasons": ["检测到非只读/危险 SQL 关键字: DELETE"]}
}
```

## 5. 常用命令

- 运行安全 Skill 测试闭环：`pytest tests/test_p0_skills.py -v`
- 提交前影响面核验：`gitnexus_detect_changes()`
- Hook 链路快速自检：`python -c "from backend.skills import create_hook_manager; print(create_hook_manager())"`