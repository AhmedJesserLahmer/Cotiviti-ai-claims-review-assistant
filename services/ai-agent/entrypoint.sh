#!/usr/bin/env bash
set -euo pipefail

echo "Starting ai-agent..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8002}" \
  --workers "${UVICORN_WORKERS:-1}" \
  --timeout-graceful-shutdown 30 \
  --no-access-log
