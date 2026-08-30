#!/usr/bin/env bash
set -euo pipefail

DB_FILE="${DB_PATH:-/app/data/sokora.db}"
SEED_FILE="/app/seed/sokora.db"

if [[ ! -f "${DB_FILE}" ]]; then
  if [[ -f "${SEED_FILE}" ]]; then
    echo "[entrypoint] database not found, seeding from image copy -> ${DB_FILE}"
    mkdir -p "$(dirname "${DB_FILE}")"
    cp "${SEED_FILE}" "${DB_FILE}"
  else
    echo "[entrypoint] database not found and no seed available; app will initialize on startup"
  fi
fi

exec "$@"
