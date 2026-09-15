"""
Module: pipeline.py
Project: Campus360 Analytics Platform
Purpose: Master end-to-end ETL pipeline runner for the Data Engineering layer:
         Extract -> Transform & Clean -> Key Stitching -> SQLite Warehouse Load -> Data Quality Validation
"""

import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from etl.extract import extract_all_sources
from etl.transform import transform_and_stitch
from etl.load import load_warehouse
from etl.validate import run_data_quality_tests


def run_pipeline():
    """Runs the master ETL pipeline from raw CSV extraction to SQLite warehouse loading & validation."""
    start_time = time.time()
    print("=" * 80)
    print("      CAMPUS360 DATA ENGINEERING LAYER — MASTER ETL PIPELINE RUNNER     ")
    print("=" * 80)

    # 1. EXTRACT
    print("\n>>> STAGE 1: EXTRACTION")
    raw_dfs = extract_all_sources()

    # 2. TRANSFORM & STITCH
    print("\n>>> STAGE 2: TRANSFORMATION & DATA STITCHING")
    warehouse_dfs, master_df = transform_and_stitch(raw_dfs)

    # 3. LOAD
    print("\n>>> STAGE 3: SQLITE WAREHOUSE LOADING")
    load_counts = load_warehouse(warehouse_dfs, master_df)

    # 4. VALIDATE
    print("\n>>> STAGE 4: AUTOMATED DATA QUALITY VALIDATION")
    validation_results = run_data_quality_tests()

    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"ETL PIPELINE COMPLETED SUCCESSFULLY in {elapsed:.2f} seconds.")
    print("=" * 80 + "\n")
    return {
        "raw_counts": {k: len(v) for k, v in raw_dfs.items()},
        "master_students": len(master_df),
        "warehouse_counts": load_counts,
        "validation": validation_results,
    }


if __name__ == "__main__":
    run_pipeline()
