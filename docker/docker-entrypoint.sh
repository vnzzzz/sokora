#!/usr/bin/env bash
set -euo pipefail

# Keep the image provider-independent: managed platforms can inject PORT while
# local Docker continues to use the default 8000 listener.
if [[ $# -eq 0 ]]; then
  set -- uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec "$@"
