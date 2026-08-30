#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-sqlite:///data/sokora.db}"
SEED_FILE="/app/seed/sokora.db"

if [[ "${DATABASE_URL}" == sqlite:///* ]]; then
  DB_FILE="${DATABASE_URL#sqlite:///}"
  DB_FILE="${DB_FILE%%\?*}"

  if [[ "${DB_FILE}" != ":memory:" ]]; then
    if [[ "${DB_FILE}" != /* ]]; then
      DB_FILE="/app/${DB_FILE}"
    fi

    if [[ ! -f "${DB_FILE}" ]]; then
      if [[ -f "${SEED_FILE}" ]]; then
        echo "[entrypoint] database not found, seeding from image copy -> ${DB_FILE}"
        mkdir -p "$(dirname "${DB_FILE}")"
        cp "${SEED_FILE}" "${DB_FILE}"
      else
        echo "[entrypoint] database not found and no seed available; app will initialize on startup"
      fi
    fi
  fi
else
  echo "[entrypoint] non-SQLite DATABASE_URL; skipping image database seed copy"
fi

exec "$@"
