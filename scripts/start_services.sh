#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
FRONTEND_REACT_DIR="$ROOT_DIR/frontend-react"
LOG_DIR="$ROOT_DIR/logs"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
FRONTEND_REACT_PORT="${FRONTEND_REACT_PORT:-5174}"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"

WITH_GATEWAY=0
WITH_CELERY=0
SKIP_DOCKER=0
KILL_FIRST=1
ACTION="start"

usage() {
  cat <<EOF
Usage: scripts/start_services.sh [options]

Options:
  --with-gateway   Start optional FastAPI gateway on port ${GATEWAY_PORT}
  --with-celery    Start optional Celery worker locally
  --skip-docker    Do not restart PostgreSQL/Redis containers
  --no-kill        Do not stop existing app processes before starting
  --stop           Stop app processes and Docker Compose services, then exit
  --status         Print current service status, then exit
  -h, --help       Show this help

Environment overrides:
  BACKEND_PORT=${BACKEND_PORT}
  FRONTEND_PORT=${FRONTEND_PORT}
  FRONTEND_REACT_PORT=${FRONTEND_REACT_PORT}
  GATEWAY_PORT=${GATEWAY_PORT}
EOF
}

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

require_cmd() {
  have_cmd "$1" || fail "Required command not found: $1"
}

port_pids() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

show_port_status() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(port_pids "$port")"
  if [[ -n "$pids" ]]; then
    log "$label port $port is in use by PID(s): $(echo "$pids" | tr '\n' ' ')"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
  else
    log "$label port $port is free"
  fi
}

stop_port() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(port_pids "$port")"
  if [[ -z "$pids" ]]; then
    log "$label port $port has no listening process"
    return
  fi

  log "Stopping $label process(es) on port $port: $(echo "$pids" | tr '\n' ' ')"
  echo "$pids" | xargs kill -TERM 2>/dev/null || true
  sleep 2

  pids="$(port_pids "$port")"
  if [[ -n "$pids" ]]; then
    log "Force killing remaining $label process(es) on port $port: $(echo "$pids" | tr '\n' ' ')"
    echo "$pids" | xargs kill -KILL 2>/dev/null || true
    sleep 1
  fi
}

stop_non_docker_port() {
  local port="$1"
  local label="$2"
  local pids
  local pid
  local command_name
  local remaining=()

  pids="$(port_pids "$port")"
  if [[ -z "$pids" ]]; then
    log "$label port $port has no residual listening process"
    return
  fi

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_name="$(ps -p "$pid" -o comm= 2>/dev/null || true)"
    case "$command_name" in
      *Docker*|*docker*|com.docker*)
        log "Keeping Docker-owned listener on $label port $port: PID $pid ($command_name)"
        ;;
      *)
        if [[ "$command_name" == *"/opt/homebrew/opt/redis/bin/redis-server"* ]] && have_cmd brew; then
          log "Stopping Homebrew Redis service before killing residual Redis process"
          brew services stop redis >/dev/null 2>&1 || true
        fi
        remaining+=("$pid")
        ;;
    esac
  done <<< "$pids"

  if [[ "${#remaining[@]}" -eq 0 ]]; then
    return
  fi

  log "Stopping residual non-Docker $label process(es) on port $port: ${remaining[*]}"
  printf '%s\n' "${remaining[@]}" | xargs kill -TERM 2>/dev/null || true
  sleep 2

  pids="$(port_pids "$port")"
  remaining=()
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_name="$(ps -p "$pid" -o comm= 2>/dev/null || true)"
    case "$command_name" in
      *Docker*|*docker*|com.docker*)
        ;;
      *)
        remaining+=("$pid")
        ;;
    esac
  done <<< "$pids"

  if [[ "${#remaining[@]}" -gt 0 ]]; then
    log "Force killing residual non-Docker $label process(es) on port $port: ${remaining[*]}"
    printf '%s\n' "${remaining[@]}" | xargs kill -KILL 2>/dev/null || true
    sleep 1
  fi
}

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif have_cmd docker-compose; then
    docker-compose "$@"
  else
    fail "Docker Compose is required. Install Docker Desktop or docker-compose."
  fi
}

compose_services_status() {
  if [[ "$SKIP_DOCKER" -eq 1 ]]; then
    log "Docker status skipped"
    return
  fi

  if have_cmd docker || have_cmd docker-compose; then
    (cd "$BACKEND_DIR" && docker_compose ps) || true
  else
    log "Docker is not installed"
  fi
}

stop_infra() {
  if [[ "$SKIP_DOCKER" -eq 1 ]]; then
    log "Skipping Docker Compose stop"
    return
  fi

  require_cmd docker
  log "Stopping Docker Compose services in backend/"
  (cd "$BACKEND_DIR" && docker_compose down)
  stop_non_docker_port 5432 "PostgreSQL"
  stop_non_docker_port 6379 "Redis"
}

start_infra() {
  if [[ "$SKIP_DOCKER" -eq 1 ]]; then
    log "Skipping Docker Compose startup"
    return
  fi

  require_cmd docker
  log "Starting PostgreSQL and Redis containers"
  (cd "$BACKEND_DIR" && docker_compose up -d postgres redis)
}

ensure_node_deps() {
  local dir="$1"
  local label="$2"
  if [[ ! -d "$dir/node_modules" ]]; then
    fail "$label dependencies are missing. Run 'npm install' in $dir first."
  fi
}

ensure_venv() {
  [[ -x "$ROOT_DIR/venv/bin/python" ]] || fail "Python venv is missing at $ROOT_DIR/venv"
}

spawn_detached() {
  local workdir="$1"
  local logfile="$2"
  local pidfile="$3"
  shift 3

  "$ROOT_DIR/venv/bin/python" - "$workdir" "$logfile" "$pidfile" "$@" <<'PY'
import os
import subprocess
import sys

workdir = sys.argv[1]
logfile = sys.argv[2]
pidfile = sys.argv[3]
cmd = sys.argv[4:]

os.makedirs(os.path.dirname(logfile), exist_ok=True)
with open(logfile, "ab", buffering=0) as log:
    process = subprocess.Popen(
        cmd,
        cwd=workdir,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )

with open(pidfile, "w", encoding="utf-8") as handle:
    handle.write(f"{process.pid}\n")
PY
}

start_backend() {
  ensure_venv
  mkdir -p "$LOG_DIR"
  log "Starting backend on port $BACKEND_PORT"
  spawn_detached "$BACKEND_DIR" "$LOG_DIR/backend-${BACKEND_PORT}.log" "$LOG_DIR/backend-${BACKEND_PORT}.pid" \
    "$ROOT_DIR/venv/bin/python" -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    --ws-max-size 104857600
}

start_gateway() {
  ensure_venv
  mkdir -p "$LOG_DIR"
  log "Starting gateway on port $GATEWAY_PORT"
  spawn_detached "$BACKEND_DIR" "$LOG_DIR/gateway-${GATEWAY_PORT}.log" "$LOG_DIR/gateway-${GATEWAY_PORT}.pid" \
    "$ROOT_DIR/venv/bin/python" -m uvicorn gateway:app \
    --host 0.0.0.0 \
    --port "$GATEWAY_PORT" \
    --reload
}

start_celery() {
  ensure_venv
  mkdir -p "$LOG_DIR"
  log "Starting local Celery worker"
  spawn_detached "$BACKEND_DIR" "$LOG_DIR/celery-worker.log" "$LOG_DIR/celery-worker.pid" \
    "$ROOT_DIR/venv/bin/celery" -A worker.celery_app worker --loglevel=info
}

start_frontend() {
  ensure_node_deps "$FRONTEND_DIR" "frontend"
  mkdir -p "$LOG_DIR"
  log "Starting frontend on port $FRONTEND_PORT"
  spawn_detached "$FRONTEND_DIR" "$LOG_DIR/frontend-${FRONTEND_PORT}.log" "$LOG_DIR/frontend-${FRONTEND_PORT}.pid" \
    npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort
}

start_frontend_react() {
  ensure_node_deps "$FRONTEND_REACT_DIR" "frontend-react"
  mkdir -p "$LOG_DIR"
  log "Starting frontend-react on port $FRONTEND_REACT_PORT"
  spawn_detached "$FRONTEND_REACT_DIR" "$LOG_DIR/frontend-react-${FRONTEND_REACT_PORT}.log" "$LOG_DIR/frontend-react-${FRONTEND_REACT_PORT}.pid" \
    npm run dev -- --host 0.0.0.0 --port "$FRONTEND_REACT_PORT" --strictPort
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempt
  for attempt in {1..60}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$label is reachable: $url"
      return 0
    fi
    sleep 1
  done
  fail "$label did not become reachable: $url"
}

wait_for_port() {
  local port="$1"
  local label="$2"
  local attempt
  for attempt in {1..60}; do
    if [[ -n "$(port_pids "$port")" ]]; then
      log "$label is listening on port $port"
      return 0
    fi
    sleep 1
  done
  fail "$label did not start listening on port $port"
}

print_status() {
  show_port_status 5432 "PostgreSQL"
  show_port_status 6379 "Redis"
  show_port_status "$BACKEND_PORT" "Backend"
  show_port_status "$FRONTEND_PORT" "Frontend"
  show_port_status "$FRONTEND_REACT_PORT" "Frontend React"
  show_port_status "$GATEWAY_PORT" "Gateway"
  compose_services_status
}

stop_apps() {
  stop_port "$FRONTEND_REACT_PORT" "Frontend React"
  stop_port "$FRONTEND_PORT" "Frontend"
  stop_port "$GATEWAY_PORT" "Gateway"
  stop_port "$BACKEND_PORT" "Backend"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --with-gateway)
        WITH_GATEWAY=1
        ;;
      --with-celery)
        WITH_CELERY=1
        ;;
      --skip-docker)
        SKIP_DOCKER=1
        ;;
      --no-kill)
        KILL_FIRST=0
        ;;
      --stop)
        ACTION="stop"
        ;;
      --status)
        ACTION="status"
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown option: $1"
        ;;
    esac
    shift
  done
}

main() {
  parse_args "$@"
  require_cmd lsof
  require_cmd curl
  require_cmd npm

  case "$ACTION" in
    status)
      print_status
      exit 0
      ;;
    stop)
      print_status
      stop_apps
      stop_infra
      log "Stopped requested services"
      exit 0
      ;;
  esac

  log "Current service status before startup"
  print_status

  if [[ "$KILL_FIRST" -eq 1 ]]; then
    stop_apps
    stop_infra
  fi

  start_infra
  wait_for_port 5432 "PostgreSQL"
  wait_for_port 6379 "Redis"

  start_backend
  wait_for_http "http://127.0.0.1:${BACKEND_PORT}/docs" "Backend"

  if [[ "$WITH_GATEWAY" -eq 1 ]]; then
    start_gateway
    wait_for_http "http://127.0.0.1:${GATEWAY_PORT}/docs" "Gateway"
  fi

  if [[ "$WITH_CELERY" -eq 1 ]]; then
    start_celery
  fi

  start_frontend
  wait_for_http "http://127.0.0.1:${FRONTEND_PORT}/" "Frontend"

  start_frontend_react
  wait_for_http "http://127.0.0.1:${FRONTEND_REACT_PORT}/" "Frontend React"

  log "Startup complete"
  log "Backend:        http://localhost:${BACKEND_PORT}/docs"
  log "Frontend:       http://localhost:${FRONTEND_PORT}/"
  log "Frontend React: http://localhost:${FRONTEND_REACT_PORT}/"
  if [[ "$WITH_GATEWAY" -eq 1 ]]; then
    log "Gateway:        http://localhost:${GATEWAY_PORT}/docs"
  fi
  log "Logs:           $LOG_DIR"
}

main "$@"
