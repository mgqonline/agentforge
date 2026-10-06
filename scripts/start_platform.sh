#!/usr/bin/env bash
# ==============================================================================
# AgentForge · 智炼工坊 · 一键全栈服务启动与多租户工作台托管脚本
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
REACT_FRONTEND_DIR="$PROJECT_ROOT/frontend-react"

echo "=============================================================================="
echo "⚡ 启动 AgentForge · 企业多租户 AI 工作台"
echo "=============================================================================="

# 0. 后端 Python 执行环境自检
# 背景：本机存在多套 Python (pyenv / miniconda base / conda 子环境)，不同 Shell 的
# PATH 顺序会让裸 `python3` 解析到缺依赖的环境，导致 uvicorn/worker 启动时抛
# ModuleNotFoundError 并崩溃退出 (曾出现 fastapi、deepface、faster_whisper 缺失)，
# 而后端端口(6001)一直不监听，前端只会提示"连接认证中枢失败"，不易定位原因。
# 解决方式：固定使用仓库内自带的虚拟环境 backend/.venv (由
# scripts/setup_backend_env.sh 创建，已预装 requirements.txt 全部依赖)，
# 不再依赖当前 Shell 的 PATH 猜测解释器。
echo "🔍 [0/3] 校验后端 Python 执行环境..."
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python3"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "  ⚠️ 未发现预置虚拟环境 ($VENV_PYTHON)，正在自动构建 (首次运行可能耗时较久)..."
  bash "$PROJECT_ROOT/scripts/setup_backend_env.sh" || {
    echo "  ❌ 自动构建虚拟环境失败，请手动执行 scripts/setup_backend_env.sh 排查。"
    exit 1
  }
fi

if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "  ❌ 虚拟环境缺少 fastapi/uvicorn，请重新执行 scripts/setup_backend_env.sh 修复依赖。"
  exit 1
fi

PYTHON_BIN="$VENV_PYTHON"
echo "  ✅ 后端将使用固定虚拟环境解释器: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

# 0.5 PostgreSQL 容器编排与账号密码自动对齐
# 背景：Postgres 仅在数据卷首次初始化时读取 POSTGRES_PASSWORD。若容器早已创建
# (例如运行了数周)，后续修改 .env 中的密码不会生效，后端会以新密码连接失败。
# 本段负责：停止旧容器 -> 按 .env 凭据重建/重启 -> 用 ALTER USER 把库内账号密码
# 对齐到 .env，保证 DATABASE_URL / ASYNC_DATABASE_URL 与库内实际密码一致。
echo "🔍 [0.5/3] 校验并同步 PostgreSQL 容器与账号密码..."

COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# 只有在项目配置了 docker-compose 且本机可访问 docker 守护进程时才接管数据库。
if [ -f "$COMPOSE_FILE" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then

  # 从 .env 读取数据库凭据 (缺失时回落到 compose 默认约定值)
  ENV_FILE="$PROJECT_ROOT/.env"
  get_env() {
    # $1=键名  $2=回退默认值；仅取首个匹配，去除首尾空白与成对包裹引号
    local line
    line=$(grep -E "^[[:space:]]*$1=" "$ENV_FILE" 2>/dev/null | head -n 1) || true
    if [ -z "$line" ]; then
      echo "$2"
    else
      # 注意：只剥离成对的引号，不能用 s/^.// 之类无条件截断首尾字符
      printf '%s' "${line#*=}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
        -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/"
    fi
  }

  PG_USER="$(get_env POSTGRES_USER aiuser)"
  PG_PASSWORD="$(get_env POSTGRES_PASSWORD '')"
  PG_DB="$(get_env POSTGRES_DB ailearning)"

  # 密码为空则拒绝继续：避免静默使用弱口令启动数据库
  if [ -z "$PG_PASSWORD" ]; then
    echo "  ❌ 未在 .env 中配置 POSTGRES_PASSWORD，拒绝启动数据库。"
    echo "     请在 $ENV_FILE 中补充：POSTGRES_PASSWORD=<强密码>"
    exit 1
  fi
  echo "  🔑 数据库账号: $PG_USER | 目标库: $PG_DB | 密码: 已配置(长度 ${#PG_PASSWORD})"

  # 1) 停止并清理占用固定容器名的旧容器
  #    compose 用 container_name 固定命名容器，若同名容器属于「别的 compose 项目」
  #    (例如从旧目录 /project/ailearning 启动过)，compose stop 会因为项目名不匹配而
  #    完全看不到它，随后 up 就会因名字冲突直接失败。这里显式按名字清理。
  echo "  🛑 停止并清理现有 AgentForge 容器 (postgres/redis/backend/frontend)..."

  # 1a) 先按当前项目停止 (正常路径，最快且不丢数据)
  docker compose -f "$COMPOSE_FILE" stop postgres redis backend frontend >/dev/null 2>&1 || true

  # 1b) 再按容器名逐个排查：只处理「同名但属于其他 compose 项目」的遗留容器。
  #     数据都在命名卷里 (postgres_data / redis_data)，删除容器不丢数据；
  #     只有卷被显式删除才会丢，所以这里只 rm 容器、绝不动卷。
  CURRENT_PROJECT="$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null \
    | sed -n 's/^[[:space:]]*"name":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  [ -z "$CURRENT_PROJECT" ] && CURRENT_PROJECT="$(basename "$PROJECT_ROOT")"

  CONFLICT_FOUND=0
  for cname in ailearning_postgres ailearning_redis ailearning_backend ailearning_frontend; do
    exists="$(docker ps -a --filter "name=^/${cname}$" --format '{{.Names}}' 2>/dev/null | head -n 1)"
    [ -z "$exists" ] && continue

    owner="$(docker inspect "$cname" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null)"

    if [ "$owner" != "$CURRENT_PROJECT" ]; then
      CONFLICT_FOUND=1
      echo "  🧹 发现同名遗留容器 $cname (原属项目: ${owner:-非 compose 创建})，移除以便重建..."
      docker rm -f "$cname" >/dev/null 2>&1 || true
    fi
  done

  if [ "$CONFLICT_FOUND" -eq 1 ]; then
    echo "  ✅ 命名冲突已清理 (数据卷 postgres_data / redis_data 保留，数据不丢)"
  fi

  # 2) 以 .env 中的凭据启动 postgres 与 redis
  echo "  🚀 启动 postgres 与 redis 容器..."
  if ! docker compose -f "$COMPOSE_FILE" up -d postgres redis; then
    echo "  ❌ 容器启动失败。排查命令："
    echo "       docker compose -f \"$COMPOSE_FILE\" logs --tail=50 postgres redis"
    echo "       docker ps -a --filter name=ailearning"
    echo "     若仍提示名称冲突，可手动清掉同名容器后再试："
    echo "       docker rm -f ailearning_postgres ailearning_redis"
    exit 1
  fi

  # 3) 等待数据库健康就绪 (最多 60 秒)
  echo "  ⏳ 等待 PostgreSQL 健康检查通过..."
  PG_READY=0
  for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres \
         pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
      PG_READY=1
      break
    fi
    sleep 2
  done

  if [ "$PG_READY" -eq 1 ]; then
    echo "  🟢 PostgreSQL 已就绪"

    # 4) 把库内账号密码对齐到 .env (幂等操作，已一致时无副作用)
    #    使用 PGPASSWORD 定位当前口令，避免把明文密码暴露在进程 args 中。
    echo "  🔄 同步数据库账号密码至 .env 配置..."
    ALTER_OK=0

    # 4a) 先尝试无密码/旧密码直连方式执行 ALTER
    for TRY_PWD in "$PG_PASSWORD" "aipassword" ""; do
      if docker compose -f "$COMPOSE_FILE" exec -T -e PGPASSWORD="$TRY_PWD" postgres \
           psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 \
           -c "ALTER USER \"$PG_USER\" WITH PASSWORD '$PG_PASSWORD';" >/dev/null 2>&1; then
        ALTER_OK=1
        break
      fi
    done

    # 4b) 若历史密码均不可用，则回退到容器内本地信任登录 (peer/trust) 方式重置
    if [ "$ALTER_OK" -ne 1 ]; then
      echo "  ⚠️ 常规方式登录失败，尝试以容器内超级用户身份重置 (保留数据)..."
      if docker compose -f "$COMPOSE_FILE" exec -T postgres \
           psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
           -c "ALTER USER \"$PG_USER\" WITH PASSWORD '$PG_PASSWORD';" >/dev/null 2>&1; then
        ALTER_OK=1
      fi
    fi

    if [ "$ALTER_OK" -eq 1 ]; then
      echo "  ✅ 数据库账号密码已与 .env 对齐"
    else
      echo "  ⚠️ 无法自动对齐密码 (可能为数据卷旧凭据冲突)。"
      echo "     如需彻底重置且可放弃数据，请执行："
      echo "       docker compose down && docker volume rm agentforge_postgres_data && docker compose up -d postgres"
    fi

    # 5) 导出连接串，供本次会话内的后端进程直接使用
    #    URL 中的特殊字符需百分号编码 (# -> %23, @ -> %40 等)
    ENCODED_PWD=$(printf '%s' "$PG_PASSWORD" | sed -e 's/%/%25/g' -e 's/#/%23/g' -e 's/@/%40/g' -e 's/:/%3A/g' -e 's|/|%2F|g')
    export DATABASE_URL="postgresql+psycopg://${PG_USER}:${ENCODED_PWD}@localhost:5432/${PG_DB}"
    export ASYNC_DATABASE_URL="postgresql+asyncpg://${PG_USER}:${ENCODED_PWD}@localhost:5432/${PG_DB}"
    export REDIS_URL="redis://localhost:6380/0"
    echo "  🔗 已导出连接串: postgresql+asyncpg://${PG_USER}:***@localhost:5432/${PG_DB}"
  else
    echo "  ⚠️ PostgreSQL 未在预期时间内就绪，后端可能连接失败。"
    echo "     排查命令: docker compose logs --tail=50 postgres"
  fi
else
  echo "  ⏭️ 跳过：未检测到可用的 docker 守护进程或 docker-compose.yml。"
  echo "     如需容器化数据库，请先启动 Docker Desktop 后重新运行本脚本。"
fi

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
PYTHONPATH="$PROJECT_ROOT:$BACKEND_DIR" nohup "$PYTHON_BIN" -m uvicorn main:app --host 0.0.0.0 --port 6001 --ws-max-size 104857600 < /dev/null > "$PROJECT_ROOT/backend_server.log" 2>&1 &
BACKEND_PID=$!
disown $BACKEND_PID 2>/dev/null || true
echo "  ✅ 后端已在后台启动 (PID: $BACKEND_PID)，日志记录至 backend_server.log"

# 等待后端端口就绪
echo "  ⏳ 等待后端健康检查响应..."
BACKEND_READY=0
for i in {1..15}; do
  if curl -s http://127.0.0.1:6001/api/v1/curriculum/phases >/dev/null 2>&1; then
    echo "  🟢 后端网关就绪 (HTTP 200 OK)"
    BACKEND_READY=1
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "  ❌ 后端进程已提前退出，未能启动。"
    break
  fi
  sleep 1
done

if [ "$BACKEND_READY" -ne 1 ]; then
  echo "  ❌ 后端未能在预期时间内就绪，最近日志如下："
  echo "  ------------------------------------------------------------------"
  tail -n 30 "$PROJECT_ROOT/backend_server.log" 2>/dev/null | sed 's/^/  /'
  echo "  ------------------------------------------------------------------"
  echo "  ⚠️ 前端与兼容通道仍会继续启动，但登录等接口会提示\"连接认证中枢失败\"，请先排查上方日志。"
fi

# 3. 启动前端 Vite 终端 (端口 6000)
echo "💻 [2/3] 启动前端 React 沉浸式工作台 (Port 6000)..."
FRONTEND_PID=$(python3 -c "
import subprocess
log = open('$PROJECT_ROOT/frontend_server.log', 'w')
p = subprocess.Popen(['npm', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', '6000'], cwd='$REACT_FRONTEND_DIR', stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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
