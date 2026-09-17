#!/bin/bash
# ============================================================
# Hybrid RAG 系统一键启动脚本
# 运行方式：bash hybrid_rag/start.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$PROJECT_DIR/agent_env"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Hybrid RAG 系统启动中..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查虚拟环境
if [ ! -f "$ENV_DIR/bin/python" ]; then
  echo "❌ 未找到虚拟环境：$ENV_DIR"
  echo "   请先运行：python -m venv agent_env && source agent_env/bin/activate"
  exit 1
fi

# 检查 .env 文件
if [ -f "$PROJECT_DIR/.env" ]; then
  echo "✅ 已检测到 .env 文件，加载环境变量..."
  export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
else
  echo "⚠️  未找到 .env 文件，RAG 问答功能需要 DEEPSEEK_API_KEY"
fi

echo ""
echo "📡 服务地址：http://localhost:8000"
echo "📖 API 文档：http://localhost:8000/docs"
echo "🌐 Web UI：  http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$SCRIPT_DIR"
"$ENV_DIR/bin/python" -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
