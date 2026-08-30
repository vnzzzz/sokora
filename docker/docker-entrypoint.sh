#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-sqlite:///data/sokora.db}"
SEED_FILE="/app/seed/sokora.db"

if [[ "${DATABASE_URL}" == sqlite:///* ]]; then
  DB_FILE="$(
    DATABASE_URL="${DATABASE_URL}" python3 - <<'PYCODE'
import os

from app.db.session import sqlite_database_path

path = sqlite_database_path(os.environ["DATABASE_URL"])
print(path if path is not None else "")
PYCODE
  )"

  if [[ -n "${DB_FILE}" && ! -f "${DB_FILE}" ]]; then
    if [[ -f "${SEED_FILE}" ]]; then
      echo "[entrypoint] database not found, seeding from image copy -> ${DB_FILE}"
      mkdir -p "$(dirname "${DB_FILE}")"
      cp "${SEED_FILE}" "${DB_FILE}"
    else
      echo "[entrypoint] database not found and no seed available; app will initialize on startup"
    fi
  fi
else
  echo "[entrypoint] non-SQLite DATABASE_URL; skipping image database seed copy"
fi

exec "$@"
