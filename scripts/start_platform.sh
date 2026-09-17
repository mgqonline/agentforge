#!/usr/bin/env bash
# ==============================================================================
# AgentForge · 智炼工坊 · 一键全栈服务启动与多租户工作台托管脚本
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend-react"

echo "=============================================================================="
echo "⚡ 启动 AgentForge · 企业多租户 AI 工作台"
echo "=============================================================================="

# 1. 释放潜在被占用的端口 (6001 后端 / 6000, 6002 前端 / 5999 遗留)
echo "🔍 检查并释放已有端口占用..."
for port in 6001 6000 6002 5999; do
  pids=$(lsof -ti :$port 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "  🛑 终止占用端口 :$port 的进程 ($pids)"
    kill -9 $pids 2>/dev/null || true
  fi
done

# 2. 启动后端 FastAPI 服务 (端口 6001)
echo "🚀 [1/3] 启动后端 FastAPI 网关 (Port 6001)..."
cd "$BACKEND_DIR"
PYTHONPATH="$PROJECT_ROOT:$BACKEND_DIR" nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 6001 --ws-max-size 104857600 < /dev/null > "$PROJECT_ROOT/backend_server.log" 2>&1 &
BACKEND_PID=$!
disown $BACKEND_PID 2>/dev/null || true
echo "  ✅ 后端已在后台启动 (PID: $BACKEND_PID)，日志记录至 backend_server.log"

# 等待后端端口就绪
echo "  ⏳ 等待后端健康检查响应..."
for i in {1..15}; do
  if curl -s http://127.0.0.1:6001/api/v1/curriculum/phases >/dev/null 2>&1; then
    echo "  🟢 后端网关就绪 (HTTP 200 OK)"
    break
  fi
  sleep 1
done

# 3. 启动前端 Vite 终端 (端口 6000)
echo "💻 [2/3] 启动前端 React 沉浸式工作台 (Port 6000)..."
FRONTEND_PID=$(python3 -c "
import subprocess
log = open('$PROJECT_ROOT/frontend_server.log', 'w')
p = subprocess.Popen(['npm', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', '6000'], cwd='$FRONTEND_DIR', stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print(p.pid)
")
echo "  ✅ 前端已在后台启动 (PID: $FRONTEND_PID)，日志记录至 frontend_server.log"

# 4. 启动双端口无缝桥接 (端口 6002 -> 6000)
echo "🌉 [3/3] 启动双端口兼容通道 (Port 6002 -> 6000)..."
BRIDGE_PID=$(python3 -c "
import subprocess
log = open('$PROJECT_ROOT/port_bridge.log', 'w')
p = subprocess.Popen(['node', '$PROJECT_ROOT/scripts/port_bridge.js'], cwd='$PROJECT_ROOT', stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print(p.pid)
")
echo "  ✅ 兼容通道就绪 (PID: $BRIDGE_PID)，支持从 6002 与 6000 同时访问"

# 等待前端端口就绪
sleep 2

echo ""
echo "=============================================================================="
echo "🎉 AgentForge 平台启动完毕！双端口通道均已就绪："
echo "👉 旗舰主入口 (推荐): http://localhost:6000"
echo "👉 兼容通道入口 (6002): http://localhost:6002"
echo "👉 后端 OpenAPI 接口契约: http://localhost:6001/docs"
echo "=============================================================================="
echo "🔐 预置多租户体验账号与最高权限凭据："
echo "   【👑 超级管理员 (最高权限)】: admin      / AgentForge@2026  (所属租户: 企业核心智算中心)"
echo "   【🛠️ AI架构研发负责人】   : dev_lead   / Dev@2026         (所属租户: 企业核心智算中心)"
echo "   【🔬 算法科学家】         : researcher / Lab@2026         (所属租户: 创新算法实验室)"
echo "   【👁️ 只读受限访客】       : guest      / Guest@2026       (所属租户: 体验试用租户·只读)"
echo "=============================================================================="
