#!/usr/bin/env bash
set -euo pipefail

# Prepare runtime assets for devcontainer/local runs (without multi-stage Docker build).
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSETS_JSON="${ROOT_DIR}/assets/json"
HOLIDAY_CACHE="${ASSETS_JSON}/holidays_cache.json"

mkdir -p "${ASSETS_JSON}"

"${ROOT_DIR}/scripts/build_assets.sh"

if [[ ! -s "${HOLIDAY_CACHE}" ]]; then
  echo "[build] Building holiday cache -> ${HOLIDAY_CACHE}"
  (cd "${ROOT_DIR}" && poetry run python scripts/build_holiday_cache.py)
else
  echo "[skip] Holiday cache already exists: ${HOLIDAY_CACHE}"
fi

echo "[done] Dev assets are ready."
