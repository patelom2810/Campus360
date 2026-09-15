"""
Module: load.py
Project: KDAC-3 Analytics Platform
Purpose: Executes PostgreSQL DDL, loads cleaned relational tables in strict
         foreign-key order, installs analytical SQL views, and logs results.
"""

import sys
from pathlib import Path
from typing import Dict
import pandas as pd
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import SQL_DIR, get_db_engine


# Strict load order respecting foreign key constraints
LOAD_ORDER = [
    "students",
    "academic_records",
    "exam_marks",
    "attendance",
    "lifestyle",
    "skills",
    "career_preferences"
]


def execute_sql_file(engine, sql_file_path: Path):
    """Executes a multi-statement SQL script using DBAPI connection."""
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Use raw connection for clean execution of multi-statement DDL scripts
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cursor.execute(sql_content)
        raw_conn.commit()
    finally:
        raw_conn.close()


def load_warehouse(warehouse_dfs: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    """
    1. Re-executes schema.sql to guarantee a pristine relational DDL.
    2. Bulk-loads tables in foreign-key dependency order.
    3. Re-executes views.sql to establish analytical views.
    4. Verifies and returns row counts per table.
    """
    engine = get_db_engine()
    
    # 1. Initialize schema
    schema_path = SQL_DIR / "schema.sql"
    print(f"[LOAD] Initializing PostgreSQL schema from {schema_path.name}...")
    execute_sql_file(engine, schema_path)
    print(f"[LOAD] Schema initialized with all constraints, PKs, and FKs.")
    
    # 2. Bulk load tables in order
    loaded_counts = {}
    for table_name in LOAD_ORDER:
        df = warehouse_dfs.get(table_name)
        if df is None:
            raise ValueError(f"[LOAD ERROR] Missing DataFrame for table '{table_name}'")
            
        # Bulk load using multi-row insert for performance
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=2000
        )
        
        # Verify row count
        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            
        loaded_counts[table_name] = count
        print(f"[LOAD] {table_name:<20} — {count:>6} rows loaded successfully")
        
    # 3. Create analytical views
    views_path = SQL_DIR / "views.sql"
    print(f"[LOAD] Creating analytical views from {views_path.name}...")
    execute_sql_file(engine, views_path)
    print("[LOAD] Analytical views created successfully:")
    print("       • student_360_view")
    print("       • performance_features_view")
    print("       • at_risk_features_view")
    print("       • career_readiness_view")
    
    return loaded_counts


if __name__ == "__main__":
    from etl.extract import extract_all_sources
    from etl.transform import transform_and_stitch
    print("--- Running Load Stage Independently ---")
    raws = extract_all_sources()
    warehouse_tables, _ = transform_and_stitch(raws)
    counts = load_warehouse(warehouse_tables)
    print("[LOAD] All tables loaded into PostgreSQL.")
