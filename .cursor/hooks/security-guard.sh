#!/usr/bin/env bash
#
# AgentForge 安全守卫 Hook (beforeShellExecution)
# ------------------------------------------------------------------
# 依据：docs/security/安全检查清单.md、.cursor/rules/security-standards.mdc
# 职责：在 shell 命令执行前做静态审查，命中以下红线时请求人工确认：
#   1. 危险 SQL 写操作（INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE 等）
#      —— 红线 3：本系统仅允许只读查询，严禁无确认执行写操作。
#   2. 疑似硬编码凭证（sk-xxx / ghp_xxx / AKIA... 等）
#      —— 红线 1：严禁提交密钥、证书或敏感数据。
# 退出码：0 = 放行/交由上层；exit 2 = 阻断；其余非零码默认 fail-open。
#
set -euo pipefail

input=$(cat)

# 优先使用 jq 解析；不可用时回退到 python3，最后回退到原始文本匹配。
if command -v jq > /dev/null 2>&1; then
    command_str=$(printf '%s' "$input" | jq -r '.command // empty' 2>/dev/null || true)
elif command -v python3 > /dev/null 2>&1; then
    command_str=$(printf '%s' "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null || true)
else
    command_str="$input"
fi

if [ -z "$command_str" ]; then
    echo '{ "permission": "allow" }'
    exit 0
fi

# 1) 危险 SQL 写操作检测（大小写不敏感）
if printf '%s' "$command_str" | grep -Eiq '\b(INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|CREATE|GRANT|REVOKE)\b'; then
    echo '{
    "permission": "ask",
    "user_message": "此命令疑似包含数据库写操作（红线 3：本系统仅允许只读查询）。请人工确认后再执行。",
    "agent_message": "安全 Hook 拦截：检测到可能的 SQL 写操作关键字。依据 AgentForge 安全红线，生产系统禁止无确认的数据写变更，请改用只读查询或获得人工确认。"
  }'
    exit 0
fi

# 2) 硬编码凭证检测（红线 1）
if printf '%s' "$command_str" | grep -Eq '(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36,}|AIzaSy[a-zA-Z0-9_-]{33}|AKIA[0-9A-Z]{16})'; then
    echo '{
    "permission": "ask",
    "user_message": "此命令疑似包含硬编码凭证（红线 1：严禁提交密钥 / 证书 / 敏感数据）。请改用环境变量或密钥托管后重试。",
    "agent_message": "安全 Hook 拦截：检测到疑似硬编码 API Key / Token 特征。敏感配置必须通过环境变量或密钥托管注入，切勿写入命令或代码库。"
  }'
    exit 0
fi

echo '{ "permission": "allow" }'
exit 0