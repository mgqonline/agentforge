#!/usr/bin/env bash
# 开发用后端启动脚本：读取项目根目录 .env 后启动 FastAPI 服务。
# 用途：重启本地后端时确保主备模型等新配置真正生效，避免进程沿用旧环境变量。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
VENV_PY="${ROOT_DIR}/backend/.venv/bin/python3"
PORT="${PORT:-6001}"
LOG_FILE="${LOG_FILE:-/tmp/agentforge_backend.log}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少环境文件：${ENV_FILE}（请先复制 .env.example 并填写密钥）" >&2
  exit 1
fi

if [[ ! -x "${VENV_PY}" ]]; then
  echo "缺少后端虚拟环境：${VENV_PY}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

cd "${ROOT_DIR}/backend"
exec "${VENV_PY}" -m uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --ws-max-size 104857600 \
  >> "${LOG_FILE}" 2>&1