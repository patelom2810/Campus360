"""
Module: load.py
Project: Campus360 Analytics Platform
Purpose: Executes SQLite DDL, loads cleaned relational tables in strict
         foreign-key order, loads the stitched master table, installs analytical
         SQL views, and logs load counts.
"""

import sys
from pathlib import Path
from typing import Dict, Optional
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
    "career_preferences",
]


def execute_sql_file(engine, sql_file_path: Path):
    """Executes a multi-statement SQL script using DBAPI connection."""
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        if hasattr(cursor, "executescript"):
            if "views" in sql_file_path.name:
                view_names = [
                    "fact_career", "fact_lifestyle", "fact_performance", "dim_student",
                    "career_readiness_view", "at_risk_features_view", "performance_features_view",
                    "student_360_view"
                ]
                for n in view_names:
                    cursor.execute("SELECT type FROM sqlite_master WHERE name = ?", (n,))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute(f"DROP {row[0].upper()} IF EXISTS {n}")
            elif "schema" in sql_file_path.name:
                table_names = [
                    "fact_career", "fact_lifestyle", "fact_performance", "dim_student",
                    "career_readiness_view", "at_risk_features_view", "performance_features_view",
                    "student_360_view", "student_master_stitched", "career_preferences",
                    "skills", "lifestyle", "attendance", "exam_marks", "academic_records", "students"
                ]
                for n in table_names:
                    cursor.execute("SELECT type FROM sqlite_master WHERE name = ?", (n,))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute(f"DROP {row[0].upper()} IF EXISTS {n}")
            cursor.executescript(sql_content)
        else:
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
        raw_conn.commit()
    finally:
        raw_conn.close()


def load_warehouse(
    warehouse_dfs: Dict[str, pd.DataFrame],
    master_df: Optional[pd.DataFrame] = None
) -> Dict[str, int]:
    """
    1. Re-executes schema.sql to guarantee a pristine relational DDL.
    2. Bulk-loads tables in foreign-key dependency order.
    3. Bulk-loads student_master_stitched if provided.
    4. Re-executes views.sql to establish analytical views.
    5. Verifies and returns row counts per table.
    """
    engine = get_db_engine()

    # 1. Initialize schema
    schema_path = SQL_DIR / "schema.sql"
    print(f"[LOAD] Initializing SQLite schema from {schema_path.name}...")
    execute_sql_file(engine, schema_path)
    print(f"[LOAD] Schema initialized with all tables, constraints, PKs, and FKs.")

    # 2. Bulk load tables in order
    loaded_counts = {}
    for table_name in LOAD_ORDER:
        df = warehouse_dfs.get(table_name)
        if df is None:
            raise ValueError(f"[LOAD ERROR] Missing DataFrame for table '{table_name}'")

        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=500,
        )

        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

        loaded_counts[table_name] = count
        print(f"[LOAD] {table_name:<25} — {count:>6} rows loaded successfully")

    # 3. Load stitched master table
    if master_df is not None and not master_df.empty:
        master_df.to_sql(
            name="student_master_stitched",
            con=engine,
            if_exists="append",
            index=False,
            chunksize=500,
        )
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM student_master_stitched")).scalar()
        loaded_counts["student_master_stitched"] = count
        print(f"[LOAD] {'student_master_stitched':<25} — {count:>6} rows loaded successfully")

    # 4. Create analytical views
    views_path = SQL_DIR / "views.sql"
    print(f"[LOAD] Creating analytical views from {views_path.name}...")
    execute_sql_file(engine, views_path)
    print("[LOAD] Analytical views created successfully:")
    print("       • student_360_view")
    print("       • performance_features_view")
    print("       • at_risk_features_view")
    print("       • career_readiness_view")
    print("       • dim_student, fact_performance, fact_lifestyle, fact_career")

    return loaded_counts


if __name__ == "__main__":
    from etl.extract import extract_all_sources
    from etl.transform import transform_and_stitch

    print("--- Running Load Stage Independently ---")
    raws = extract_all_sources()
    warehouse_tables, master = transform_and_stitch(raws)
    counts = load_warehouse(warehouse_tables, master)
    print(f"[LOAD] Finished loading {len(counts)} tables into SQLite warehouse.")
