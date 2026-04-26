#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/claudiu/projects/email-platform"
WORKER_ROOT="/home/claudiu/projects/outreach-bot"
STATE_DIR="$ROOT/.omx/state/local-stack"
LOG_DIR="$STATE_DIR/logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

BACKEND_PID="$STATE_DIR/backend.pid"
FRONTEND_PID="$STATE_DIR/frontend.pid"
WORKER_PID="$STATE_DIR/worker.pid"

BACKEND_PORT=8000
FRONTEND_PORT=3000
WORKER_PORT=5000

pid_running() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

port_in_use() {
  local port="$1"
  lsof -i :"$port" >/dev/null 2>&1
}

worker_healthy() {
  curl -sf "http://127.0.0.1:${WORKER_PORT}/api/campaigns" >/dev/null
}

backend_healthy() {
  curl -sf "http://127.0.0.1:${BACKEND_PORT}/acquire/worker/campaigns" \
    -H 'X-API-Key: <generate-a-strong-random-key>' >/dev/null
}

frontend_healthy() {
  rm -f /tmp/email_platform_cookies.txt
  curl -sf -c /tmp/email_platform_cookies.txt \
    -H 'Content-Type: application/json' \
    -d '{"api_key":"<generate-a-strong-random-key>"}' \
    "http://127.0.0.1:${FRONTEND_PORT}/api/auth" >/dev/null && \
  curl -sfI -b /tmp/email_platform_cookies.txt "http://127.0.0.1:${FRONTEND_PORT}/acquire" >/dev/null
}

start_service() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  shift 3

  if pid_running "$pid_file"; then
    echo "$name already running (pid $(cat "$pid_file"))"
    return 0
  fi

  nohup "$@" >"$log_file" 2>&1 &
  echo $! >"$pid_file"
  echo "Started $name (pid $!)"
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  if ! pid_running "$pid_file"; then
    rm -f "$pid_file"
    echo "$name not running"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  kill "$pid" 2>/dev/null || true
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
  echo "Stopped $name"
}

health() {
  local ok=0
  if worker_healthy; then
    echo "worker: ok"
  else
    echo "worker: failed"
    ok=1
  fi
  if backend_healthy; then
    echo "backend: ok"
  else
    echo "backend: failed"
    ok=1
  fi
  if frontend_healthy; then
    echo "frontend: ok"
  else
    echo "frontend: failed"
    ok=1
  fi
  return $ok
}

status() {
  for entry in \
    "backend:$BACKEND_PID:$BACKEND_PORT" \
    "frontend:$FRONTEND_PID:$FRONTEND_PORT" \
    "worker:$WORKER_PID:$WORKER_PORT"; do
    IFS=":" read -r name pid_file port <<<"$entry"
    if pid_running "$pid_file"; then
      echo "$name running (pid $(cat "$pid_file"), port $port)"
    elif port_in_use "$port"; then
      echo "$name port $port in use by external process"
    else
      echo "$name stopped"
    fi
  done
}

start() {
  cd "$ROOT"
  if [[ ! -d "$ROOT/.venv" ]]; then
    echo "Missing core virtualenv: $ROOT/.venv" >&2
    exit 1
  fi
  if [[ ! -d "$WORKER_ROOT/.venv" ]]; then
    echo "Missing worker virtualenv: $WORKER_ROOT/.venv" >&2
    exit 1
  fi

  if port_in_use "$BACKEND_PORT" && ! pid_running "$BACKEND_PID"; then
    if backend_healthy; then
      echo "Port $BACKEND_PORT already in use by a healthy external backend; reusing it"
    else
      echo "Port $BACKEND_PORT already in use by an external process" >&2
      exit 1
    fi
  fi
  if port_in_use "$FRONTEND_PORT" && ! pid_running "$FRONTEND_PID"; then
    if frontend_healthy; then
      echo "Port $FRONTEND_PORT already in use by a healthy external frontend; reusing it"
    else
      echo "Port $FRONTEND_PORT already in use by an external process" >&2
      exit 1
    fi
  fi
  if port_in_use "$WORKER_PORT" && ! pid_running "$WORKER_PID"; then
    if worker_healthy; then
      echo "Port $WORKER_PORT already in use by a healthy external worker; reusing it"
    else
      echo "Port $WORKER_PORT already in use by an external process" >&2
      exit 1
    fi
  fi

  if ! port_in_use "$WORKER_PORT"; then
    start_service "worker" "$WORKER_PID" "$LOG_DIR/worker.log" \
      bash -lc "cd '$WORKER_ROOT' && '$WORKER_ROOT/.venv/bin/python' app.py"
    sleep 1
  fi
  if ! port_in_use "$BACKEND_PORT"; then
    start_service "backend" "$BACKEND_PID" "$LOG_DIR/backend.log" \
      bash -lc "cd '$ROOT' && DATABASE_URL=sqlite:///./email_platform.db WORKER_BASE_URL=http://127.0.0.1:${WORKER_PORT} ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}"
    sleep 1
  fi
  if ! port_in_use "$FRONTEND_PORT"; then
    start_service "frontend" "$FRONTEND_PID" "$LOG_DIR/frontend.log" \
      bash -lc "cd '$ROOT/frontend' && API_URL=http://127.0.0.1:${BACKEND_PORT} npm run dev"
  fi
  sleep 4
  status
  health
}

stop() {
  stop_service "frontend" "$FRONTEND_PID"
  stop_service "backend" "$BACKEND_PID"
  stop_service "worker" "$WORKER_PID"
}

restart() {
  stop || true
  start
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  health) health ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|health}" >&2
    exit 1
    ;;
esac
