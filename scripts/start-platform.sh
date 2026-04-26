#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/claudiu/projects/email-platform"
DOCKER_BIN="${DOCKER_BIN:-/usr/local/bin/docker}"

cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [[ ! -f worker.env ]]; then
  cp worker.env.example worker.env
  echo "Created worker.env from worker.env.example"
fi

mode="${1:-auto}"

run_docker() {
  echo "Starting via docker compose..."
  "$DOCKER_BIN" compose up --build -d
}

run_local() {
  echo "Starting via local unified stack..."
  ./scripts/unified-local-stack.sh restart
}

if [[ "$mode" == "docker" ]]; then
  run_docker
  exit 0
fi

if [[ "$mode" == "local" ]]; then
  run_local
  exit 0
fi

echo "Checking whether Docker path is healthy..."
if ./scripts/check-docker-prereqs.sh; then
  if run_docker; then
    exit 0
  fi
  echo "Docker launch failed after prereqs passed; falling back to local unified stack."
  run_local
  exit 0
fi

echo "Docker prerequisites failed; falling back to local unified stack."
run_local
