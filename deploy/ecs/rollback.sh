#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
META_FILE="$ROOT_DIR/release-meta.env"

if [[ ! -f "$META_FILE" ]]; then
  echo "[回滚] 找不到配置文件：$META_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$META_FILE"

: "${COMPOSE_FILE:?请在 release-meta.env 设置 COMPOSE_FILE}"
: "${RUNTIME_ENV_FILE:?请在 release-meta.env 设置 RUNTIME_ENV_FILE}"
: "${METADATA_DIR:?请在 release-meta.env 设置 METADATA_DIR}"

PREVIOUS_ENV="$METADATA_DIR/previous.env"
if [[ ! -f "$PREVIOUS_ENV" ]]; then
  echo "[回滚] 没有 previous.env，无法自动回滚。" >&2
  exit 1
fi

cp "$PREVIOUS_ENV" "$RUNTIME_ENV_FILE"
chmod 600 "$RUNTIME_ENV_FILE"

docker compose --env-file "$RUNTIME_ENV_FILE" -f "$COMPOSE_FILE" up -d
echo "[回滚] 已切回 previous.env"
