#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
META_FILE="$ROOT_DIR/release-meta.env"

redact() {
  sed -E \
    -e 's#(Authorization: Bearer )[A-Za-z0-9._~+/=-]+#\1***#g' \
    -e 's#(API_TOKEN|VNC_PASSWORD|GHCR_TOKEN|TOKEN|PASSWORD|SECRET)=([^[:space:]]+)#\1=***#g'
}

echo "[diagnostics] root=$ROOT_DIR"
cd "$(dirname "$ROOT_DIR")/.." 2>/dev/null || true
git status -sb 2>&1 | redact || true
git log -1 --oneline 2>&1 | redact || true

if [[ ! -f "$META_FILE" ]]; then
  echo "[diagnostics] missing release-meta.env"
  exit 0
fi

# shellcheck disable=SC1090
source "$META_FILE"

for name in GHCR_BASE COMPOSE_FILE RUNTIME_ENV_FILE API_TOKEN VNC_PASSWORD HOST_API_PORT HOST_NOVNC_PORT; do
  value="${!name:-}"
  if [[ -n "$value" ]]; then
    echo "[diagnostics] $name=SET len=${#value}"
  else
    echo "[diagnostics] $name=MISSING"
  fi
done

if [[ -n "${COMPOSE_FILE:-}" && -n "${RUNTIME_ENV_FILE:-}" ]]; then
  docker compose --env-file "$RUNTIME_ENV_FILE" -f "$COMPOSE_FILE" ps 2>&1 | redact || true
  docker compose --env-file "$RUNTIME_ENV_FILE" -f "$COMPOSE_FILE" logs --tail=120 browser-ai-relay 2>&1 | redact || true
fi
