#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for MongoDB at ${MONGO_URI:-mongodb://mongo:27017} ..."
python - <<'PY'
import os, time
from pymongo import MongoClient
uri = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
for attempt in range(30):
    try:
        MongoClient(uri, serverSelectionTimeoutMS=1000).admin.command("ping")
        print("MongoDB is up.")
        break
    except Exception:
        print(f"  ...not ready (attempt {attempt + 1}/30)")
        time.sleep(2)
else:
    raise SystemExit("MongoDB did not become available in time.")
PY

echo "Starting ai-agent..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8002}" \
  --workers "${UVICORN_WORKERS:-1}" \
  --timeout-graceful-shutdown 30 \
  --no-access-log
