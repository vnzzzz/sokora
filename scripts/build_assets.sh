#!/usr/bin/env bash
set -euo pipefail

# Build CSS (Tailwind/daisyUI) and vendor JS bundles into assets/.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDER_DIR="${ROOT_DIR}/builder"
ASSETS_DIR="${ROOT_DIR}/assets"
CSS_OUT="${ASSETS_DIR}/css/main.css"
JS_DIR="${ASSETS_DIR}/js"
LOCKFILE="${BUILDER_DIR}/package-lock.json"
LOCK_HASH_FILE="${BUILDER_DIR}/.npm-lock.hash"

mkdir -p "${ASSETS_DIR}/css" "${JS_DIR}"

if [[ ! -f "${LOCKFILE}" ]]; then
  echo "package-lock.json is missing in ${BUILDER_DIR}"
  exit 1
fi

LOCK_HASH="$(sha256sum "${LOCKFILE}" | awk '{print $1}')"

if [[ ! -d "${BUILDER_DIR}/node_modules" ]] || [[ ! -f "${LOCK_HASH_FILE}" ]] || [[ "${LOCK_HASH}" != "$(cat "${LOCK_HASH_FILE}")" ]]; then
  echo "[npm] Installing builder dependencies (npm ci)"
  (cd "${BUILDER_DIR}" && npm ci)
  echo "${LOCK_HASH}" > "${LOCK_HASH_FILE}"
else
  echo "[npm] Using cached builder dependencies"
fi

echo "[css] Building Tailwind CSS -> ${CSS_OUT}"
(cd "${BUILDER_DIR}" && npx tailwindcss -i input.css -o "${CSS_OUT}" --minify)

echo "[js] Copying vendor bundles -> ${JS_DIR}"
cp "${BUILDER_DIR}/node_modules/htmx.org/dist/htmx.min.js" "${JS_DIR}/htmx.min.js"
cp "${BUILDER_DIR}/node_modules/alpinejs/dist/cdn.min.js" "${JS_DIR}/alpine.min.js"

echo "[done] Assets are built."
