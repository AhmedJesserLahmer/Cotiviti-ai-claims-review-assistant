#!/usr/bin/env bash
set -euo pipefail

echo "Starting ml-service..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8001}" \
  --workers "${UVICORN_WORKERS:-1}" \
  --timeout-graceful-shutdown 20 \
  --no-access-log
