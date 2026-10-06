#!/usr/bin/env bash
# ==============================================================================
# AgentForge · 后端专属虚拟环境构建/修复脚本
#
# 目的：把 backend/requirements.txt 声明的全部依赖"打包"进仓库自带的虚拟环境
# backend/.venv 中，不再依赖当前终端 PATH 猜测的 python3（本机存在 pyenv /
# miniconda base / conda 子环境多套解释器，PATH 顺序不同会解析到缺依赖的
# 环境，导致 uvicorn / worker 启动时抛 ModuleNotFoundError，例如曾出现过
# fastapi、deepface、faster_whisper 缺失）。
#
# 用法：
#   bash scripts/setup_backend_env.sh          # 创建(如不存在)并安装/校验依赖
#   bash scripts/setup_backend_env.sh --rebuild # 删除旧环境后重新创建
#
# start_platform.sh 会在启动前自动调用本脚本(仅当 .venv 缺失时)。
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv"
REQUIREMENTS="$BACKEND_DIR/requirements.txt"

if [ "$1" = "--rebuild" ] && [ -d "$VENV_DIR" ]; then
  echo "🗑️  移除旧虚拟环境: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

# 1. 选择用于创建虚拟环境的基础解释器
#    优先选择已知安装了大体积依赖 (torch/opencv/chromadb 等) 的解释器，
#    并以 --system-site-packages 方式创建，避免重复下载几个 GB 的库。
BASE_PYTHON=""
BASE_CANDIDATES=()
if command -v pyenv >/dev/null 2>&1; then
  BASE_CANDIDATES+=("$(pyenv which python3 2>/dev/null || true)")
fi
BASE_CANDIDATES+=("python3" "$HOME/miniconda3/bin/python3" "$HOME/anaconda3/bin/python3" "/usr/bin/python3")

for candidate in "${BASE_CANDIDATES[@]}"; do
  if [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1; then
    BASE_PYTHON="$candidate"
    break
  fi
done

if [ -z "$BASE_PYTHON" ]; then
  echo "❌ 未找到任何可用的 python3，请先安装 Python 3.10+ 后重试。"
  exit 1
fi

echo "🧩 基础解释器: $BASE_PYTHON ($("$BASE_PYTHON" --version 2>&1))"

# 2. 创建虚拟环境 (若不存在)
if [ ! -x "$VENV_DIR/bin/python3" ]; then
  echo "📦 创建虚拟环境: $VENV_DIR (--system-site-packages，复用已安装的大体积依赖)"
  "$BASE_PYTHON" -m venv "$VENV_DIR" --system-site-packages
else
  echo "📦 已存在虚拟环境: $VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python3"

# 3. 安装/校验 requirements.txt 全部依赖
echo "⬇️  安装/校验依赖 ($REQUIREMENTS)..."
"$VENV_PYTHON" -m pip install --upgrade pip -q
"$VENV_PYTHON" -m pip install -r "$REQUIREMENTS"

# 4. 关键模块导入自检 (覆盖历史上出现过缺失的模块)
echo "🔬 关键模块导入自检..."
"$VENV_PYTHON" - <<'PYEOF'
import importlib
import sys

mods = [
    "fastapi", "uvicorn", "langchain", "langgraph", "openai", "chromadb",
    "sentence_transformers", "pymysql", "sqlalchemy", "celery", "redis",
    "psycopg2", "asyncpg", "psycopg", "easyocr", "cv2", "faster_whisper",
    "deepface", "mcp",
]

missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        missing.append((m, str(e)))

if missing:
    print("❌ 以下模块仍无法导入：")
    for name, err in missing:
        print(f"   - {name}: {err}")
    sys.exit(1)
else:
    print(f"✅ 全部 {len(mods)} 个关键模块导入正常。")
PYEOF

echo ""
echo "=============================================================================="
echo "🎉 后端虚拟环境就绪: $VENV_DIR"
echo "👉 之后 scripts/start_platform.sh 会自动使用该环境启动后端，无需再关心"
echo "   当前终端 PATH 指向哪个 python3。"
echo "=============================================================================="
