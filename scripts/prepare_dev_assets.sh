#!/usr/bin/env bash
set -euo pipefail

# Prepare runtime assets for devcontainer/local runs (without multi-stage Docker build).
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSETS_JS="${ROOT_DIR}/assets/js"
ASSETS_JSON="${ROOT_DIR}/assets/json"
HOLIDAY_CACHE="${ASSETS_JSON}/holidays_cache.json"

mkdir -p "${ASSETS_JS}" "${ASSETS_JSON}"

download_if_missing() {
  local url="$1"
  local dest="$2"
  local name="$3"

  if [[ -s "${dest}" ]]; then
    echo "[skip] ${name} already exists: ${dest}"
    return
  fi

  echo "[get] Downloading ${name} -> ${dest}"
  curl -fL "${url}" -o "${dest}"
}

download_if_missing "https://unpkg.com/htmx.org/dist/htmx.min.js" "${ASSETS_JS}/htmx.min.js" "htmx"
download_if_missing "https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js" "${ASSETS_JS}/alpine.min.js" "Alpine.js"

if [[ ! -s "${HOLIDAY_CACHE}" ]]; then
  echo "[build] Building holiday cache -> ${HOLIDAY_CACHE}"
  (cd "${ROOT_DIR}" && poetry run python scripts/build_holiday_cache.py)
else
  echo "[skip] Holiday cache already exists: ${HOLIDAY_CACHE}"
fi

echo "[done] Dev assets are ready."
