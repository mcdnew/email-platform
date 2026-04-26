#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/claudiu/projects/email-platform"
DOCKER_BIN="${DOCKER_BIN:-/usr/local/bin/docker}"

check_cmd() {
  local name="$1"
  shift
  echo
  echo "== $name =="
  if "$@"; then
    return 0
  else
    echo "[FAIL] $name"
    return 1
  fi
}

check_http() {
  local url="$1"
  echo
  echo "== curl $url =="
  if curl -I --max-time 15 "$url"; then
    return 0
  else
    echo "[FAIL] curl $url"
    return 1
  fi
}

failures=0

check_cmd "docker version" "$DOCKER_BIN" --version || failures=$((failures + 1))
check_cmd "docker context ls" "$DOCKER_BIN" context ls || failures=$((failures + 1))
check_cmd "docker ps" "$DOCKER_BIN" ps || failures=$((failures + 1))
check_cmd "docker compose version" "$DOCKER_BIN" compose version || failures=$((failures + 1))
check_cmd "docker compose config" "$DOCKER_BIN" compose -f "$ROOT/docker-compose.yml" config >/dev/null || failures=$((failures + 1))

check_http "https://registry-1.docker.io" || failures=$((failures + 1))
check_http "https://auth.docker.io" || failures=$((failures + 1))

for image in python:3.10-slim python:3.12-slim node:20-alpine caddy:2; do
  echo
  echo "== docker manifest inspect $image =="
  if "$DOCKER_BIN" manifest inspect "$image" >/dev/null 2>&1; then
    echo "[OK] manifest available for $image"
  else
    echo "[FAIL] manifest unavailable for $image"
    failures=$((failures + 1))
  fi
done

echo
if [[ "$failures" -eq 0 ]]; then
  echo "All Docker prerequisites passed."
else
  echo "$failures Docker prerequisite checks failed."
fi

exit "$failures"
