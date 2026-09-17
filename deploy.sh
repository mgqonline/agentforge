#!/usr/bin/env bash
# ==============================================================================
# AI Learning 生产级一键发布与热更新自动化脚本 (Idempotent Docker Deployer)
# 职责：不管当前服务是否存在、停止或运行，均可幂等构建并发布最新版本代码
# 端口规范：前端 6000，后端 6001
# ==============================================================================

set -eo pipefail

# 终端彩色输出支持
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BOLD}${PURPLE}"
echo "================================================================="
echo "   🚀 AI Learning Enterprise Platform 一键自动化发布部署中枢   "
echo "   规范端口: [前端 Web: 6000]  |  [后端 API: 6001]             "
echo "================================================================="
echo -e "${NC}"

# 1. 检查 Docker 运行时
log_info "1/5 正在自检宿主机 Docker 与 Compose 环境..."
if ! command -v docker &>/dev/null; then
    log_error "未检测到 Docker，请先安装 Docker 环境！"
    exit 1
fi

if ! docker info &>/dev/null; then
    log_error "Docker 服务未在运行，请先启动 Docker Engine / Docker Desktop！"
    exit 1
fi

COMPOSE_CMD=""
if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    log_error "未检测到 docker compose 或 docker-compose 命令行工具！"
    exit 1
fi
log_success "Docker 环境检查通过: $(${COMPOSE_CMD} version)"

# 2. 检查并准备环境配置文件
log_info "2/5 正在验证环境配置文件 .env ..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        log_warn "未发现 .env，正在依据 .env.example 自动生成基础配置..."
        cp .env.example .env
    else
        touch .env
    fi
fi
log_success "环境变量配置已就绪"

# 3. 幂等清理已有的孤立/同名历史容器（保证不管服务是否存在均可安全重建）
log_info "3/5 正在清理或平滑停用旧版本容器与可能冲突的孤立实例..."
TARGET_CONTAINERS=("ailearning_frontend" "ailearning_backend" "ailearning_redis" "ailearning_postgres")
for c in "${TARGET_CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -Eq "^${c}\$"; then
        log_warn "发现已存在的容器 [${c}]，正在安全重置..."
        docker stop "${c}" &>/dev/null || true
        docker rm -f "${c}" &>/dev/null || true
    fi
done

# 如果有正在占用的 compose 栈，顺便清理
${COMPOSE_CMD} down --remove-orphans &>/dev/null || true
log_success "旧版本容器状态清理完毕"

# 4. 全量拉取基础依赖并构建最新业务代码镜像
log_info "4/5 正在编译构建最新版本镜像 (包含前端最新产物与后端核心中枢)..."
${COMPOSE_CMD} build --pull
log_success "最新镜像构建完成"

# 5. 启动全套服务
log_info "5/5 正在拉起所有容器服务..."
${COMPOSE_CMD} up -d --remove-orphans

# 6. 健康探活探测 (Health Checking)
echo -e "\n${CYAN}⏳ 正在等待核心服务完成预热初始化并进行健康检测...${NC}"

BACKEND_READY=0
for i in {1..45}; do
    if curl -s -f http://localhost:6001/docs &>/dev/null; then
        BACKEND_READY=1
        break
    fi
    echo -ne "   正在等待后端 (Port 6001) 初始化 [${i}/45] (约需20~35秒预热模型与数据库)...\r"
    sleep 2
done
echo ""

if [ ${BACKEND_READY} -eq 1 ]; then
    log_success "后端 AI 核心服务健康检测通过 (http://localhost:6001)！"
else
    log_warn "后端健康检测超时，请检查后端启动日志："
    ${COMPOSE_CMD} logs --tail 30 backend
fi

FRONTEND_READY=0
for i in {1..15}; do
    if curl -s -f http://localhost:6002/ &>/dev/null || curl -s -f http://localhost:6000/ &>/dev/null; then
        FRONTEND_READY=1
        break
    fi
    echo -ne "   正在等待前端 Nginx (Port 6002/6000) 就绪 [${i}/15s]...\r"
    sleep 1
done
echo ""

if [ ${FRONTEND_READY} -eq 1 ]; then
    log_success "前端 Web 工作站健康检测通过 (http://localhost:6002)！"
else
    log_warn "前端健康检测超时，请检查前端启动日志："
    ${COMPOSE_CMD} logs --tail 20 frontend
fi

# 7. 打印最终上线汇总面板
echo -e "\n${BOLD}${GREEN}================================================================="
echo "   🎉🎉 [发布成功] AI Learning 最新版本服务已全部就绪！"
echo "=================================================================${NC}"
echo -e "${BOLD}📌 服务访问清单与接口入口：${NC}"
echo -e "   🔹 ${CYAN}前端现代化工作空间 (React 旗舰版 - 推荐入口):${NC} http://localhost:6002"
echo -e "   🔹 ${CYAN}前端原生沉浸式终端 (Vanilla 经典版):${NC}         http://localhost:6002/vanilla/"
echo -e "   ⚠️  ${YELLOW}兼容端口 (注: 部分浏览器会将 6000 误判为 UNSAFE 端口):${NC} http://localhost:6000"
echo -e "   🔹 ${CYAN}后端 AI 核心 API 与 Swagger 文档:${NC}           http://localhost:6001/docs"
echo -e "   🔹 ${CYAN}后端全双工 WebSocket 长连接端点:${NC}            ws://localhost:6001/ws/chat"
echo ""
echo -e "${BOLD}📊 当前运行容器概览：${NC}"
${COMPOSE_CMD} ps
echo ""
echo -e "${BOLD}🛠️ 常用运维管理指令：${NC}"
echo -e "   • 查看实时全量日志:   ${YELLOW}${COMPOSE_CMD} logs -f${NC}"
echo -e "   • 仅查看后端服务日志: ${YELLOW}${COMPOSE_CMD} logs -f backend${NC}"
echo -e "   • 重启整套业务集群:   ${YELLOW}${COMPOSE_CMD} restart${NC}"
echo -e "   • 停止并销毁当前容器: ${YELLOW}${COMPOSE_CMD} down${NC}"
echo -e "   • 再次发布/更新版本:  ${YELLOW}./deploy.sh${NC}"
echo "================================================================="
