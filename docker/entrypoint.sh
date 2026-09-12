#!/bin/bash
# Campus360 API entrypoint:
# 1. If DB_ENGINE=postgres (default), wait for Postgres and run ETL load if tables are empty
# 2. Start uvicorn

set -e

echo "=============================="
echo "Campus360 API Entrypoint"
echo "DB_ENGINE=${DB_ENGINE:-postgres}"
echo "=============================="

if [ "${DB_ENGINE:-postgres}" = "postgres" ]; then
    echo "[ENTRYPOINT] Checking if warehouse tables need population..."
    python - <<'PYEOF'
import os, sys, time
from pathlib import Path
sys.path.insert(0, "/app")
from sqlalchemy import text
from src.etl.load import create_warehouse_engine, load_star_schema

# Wait for postgres with retries (healthcheck should already pass, but belt-and-suspenders)
for attempt in range(10):
    try:
        engine, engine_type = create_warehouse_engine()
        if engine_type != "postgres":
            print(f"[ENTRYPOINT] engine_type={engine_type}, skipping ETL load")
            sys.exit(0)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM dim_student")).scalar()
        print(f"[ENTRYPOINT] dim_student already has {count} rows — skipping ETL load")
        sys.exit(0)
    except Exception as e:
        err_str = str(e)
        if "does not exist" in err_str or "UndefinedTable" in err_str or "relation" in err_str:
            # Table doesn't exist yet — need to load
            break
        print(f"[ENTRYPOINT] Waiting for Postgres... attempt {attempt+1}/10: {e}")
        time.sleep(3)

print("[ENTRYPOINT] Tables are empty/missing — running ETL load now...")
wide_path = Path("/app/data/processed/student_master_wide.csv")
if not wide_path.exists():
    print(f"[ENTRYPOINT] ERROR: {wide_path} not found — cannot load warehouse!")
    sys.exit(1)

load_star_schema(wide_path=wide_path, save_to_db=True)
print("[ENTRYPOINT] ETL load complete.")
PYEOF

    echo "[ENTRYPOINT] ETL step done."
fi

echo "[ENTRYPOINT] Starting uvicorn..."
exec uvicorn src.api.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
