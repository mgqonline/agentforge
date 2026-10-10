# AgentForge Hook 规范

> 适用：`.cursor/hooks.json` 与 `.cursor/hooks/*` 项目级 Hook。
> 依据：Cursor Hooks schema v1；`docs/security/安全检查清单.md`。
> 原则：Hook 只做**观察、提示、拦截**，不侵入业务主流程；拦截类 Hook 必须可审计、可解释。

## 一、目录结构

```
.cursor/
├── hooks.json              # Hook 配置（schema version 1）
└── hooks/
    └── security-guard.sh   # 安全守卫 command hook（beforeShellExecution）
```

- 项目级 Hook 从**项目根目录**运行，脚本路径写作 `.cursor/hooks/xxx.sh`。
- 所有 command hook 脚本必须 `chmod +x`，并带有效 `#!/usr/bin/env bash` shebang。

## 二、已配置 Hook 清单

| 事件 | 类型 | 文件 | 职责 |
|------|------|------|------|
| `beforeSubmitPrompt` | prompt | `hooks.json` 内联 | 强制后续回复使用**简体中文**（技术名词保留英文） |
| `beforeShellExecution` | command | `.cursor/hooks/security-guard.sh` | 拦截疑似 SQL 写操作与硬编码凭证（红线 1、3） |

### 2.1 中文回复规范（beforeSubmitPrompt）

- 无论用户以何种语言提问，Agent 回复一律使用**简体中文**。
- 用户未显式要求其他语言时，保持中文；技术专有名词（库名、函数、命令、错误码）保留英文原写法。
- 该规范同时固化在 `.cursor/rules/project-conventions.mdc`，形成「规则 + Hook」双保险。

### 2.2 安全守卫（beforeShellExecution）

检测规则（命中即返回 `permission: ask`，请求人工确认）：

1. **危险 SQL 写操作**：`INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|CREATE|GRANT|REVOKE`
   → 红线 3：本系统仅允许只读查询。
2. **硬编码凭证**：`sk-*` / `ghp_*` / `AIzaSy*` / `AKIA*`
   → 红线 1：严禁提交密钥、证书或敏感数据。

依赖与回退：
- 解析 stdin JSON 优先用 `jq`，不可用时回退 `python3`，最后回退原始文本匹配。
- `failClosed: false`：脚本异常时**失效放行**，避免阻塞正常开发；安全由规则与 CI 兜底。

## 三、编写规范（新增 Hook 时遵循）

1. **选最窄事件**：能 `beforeShellExecution` 解决的不挂 `preToolUse`；仅为日志审计用 `after*`。
2. **返回字段仅用该事件支持项**：
   - `beforeShellExecution` / `beforeMCPExecution`：`permission`、`user_message`、`agent_message`
   - `preToolUse`：`permission`、`user_message`、`agent_message`、`updated_input`
   - `postToolUse`：`additional_context`
3. **退出码语义**：`0` 成功；`2` 阻断；其他非零默认 fail-open（除非显式 `failClosed: true`）。
4. **matcher 用 JS 正则**：不要用 `[[:space:]]` 等 POSIX 类，用 `\s` 等；先用无 matcher 跑通再收紧。
5. **脚本可移植**：依赖的外部命令（`jq`、`python3`）必须确认在 Hook 环境的 `$PATH` 中，并提供回退。
6. **不泄露隐私**：Hook 日志与提示信息中不得回显完整凭证。

## 四、本地验证

```bash
# JSON 合法性
jq empty .cursor/hooks.json

# 脚本语法
bash -n .cursor/hooks/security-guard.sh

# 行为自测
echo '{"command":"psql -c \"SELECT 1\""}' | .cursor/hooks/security-guard.sh   # allow
echo '{"command":"DROP TABLE users"}'          | .cursor/hooks/security-guard.sh   # ask
```

生产排查：在 Cursor 的 **Hooks** 设置页或 **Hooks** 输出通道查看加载与触发情况；若未加载，先移除 matcher 确认基础 Hook 生效。