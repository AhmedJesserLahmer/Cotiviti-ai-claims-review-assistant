#!/usr/bin/env bash
set -e

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

# Seeding is done by the service that owns the synthetic dataset (ml-service).
echo "Starting API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 \
  --workers "${UVICORN_WORKERS:-1}" \
  --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --timeout-graceful-shutdown 20 \
  --no-access-log
