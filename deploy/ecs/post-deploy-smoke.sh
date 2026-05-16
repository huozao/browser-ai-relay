#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
META_FILE="$ROOT_DIR/release-meta.env"

if [[ ! -f "$META_FILE" ]]; then
  echo "[post-deploy] Missing config file: $META_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$META_FILE"

: "${COMPOSE_FILE:?Please set COMPOSE_FILE in release-meta.env}"
: "${RUNTIME_ENV_FILE:?Please set RUNTIME_ENV_FILE in release-meta.env}"
: "${HEALTHCHECK_URL:?Please set HEALTHCHECK_URL in release-meta.env}"
: "${API_TOKEN:?Please set API_TOKEN in release-meta.env}"

compose=(docker compose --env-file "$RUNTIME_ENV_FILE" -f "$COMPOSE_FILE")

if ! "${compose[@]}" config --services | grep -Fxq "browser-ai-relay"; then
  echo "[post-deploy] Missing compose service: browser-ai-relay" >&2
  exit 1
fi

"${compose[@]}" ps

curl -fsS "$HEALTHCHECK_URL" >/dev/null
echo "[post-deploy] OK health $HEALTHCHECK_URL"

status_url="http://127.0.0.1:${HOST_API_PORT:-18000}/browser-status"
curl -fsS -H "Authorization: Bearer ${API_TOKEN}" "$status_url" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); print("[post-deploy] browser-status chrome_running=%s cdp_attached=%s login_status=%s" % (data.get("chrome_running"), data.get("cdp_attached"), data.get("login_status")))'

echo "[post-deploy] Smoke checks passed"
