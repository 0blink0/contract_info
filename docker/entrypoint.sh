#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit("DATABASE_URL is not set")

host = url.split("@")[-1] if "@" in url else "(unknown)"
print(f"DATABASE_URL host: {host}")

for attempt in range(45):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"  attempt {attempt + 1}/45: {exc}")
        time.sleep(2)
sys.exit("PostgreSQL not ready in time")
PY

echo "Running database migrations..."
if [ ! -f /app/alembic/env.py ]; then
  echo "ERROR: /app/alembic missing — rebuild api image after git pull"
  ls -la /app
  exit 1
fi
alembic -c /app/alembic.ini upgrade head

echo "Starting API server..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
