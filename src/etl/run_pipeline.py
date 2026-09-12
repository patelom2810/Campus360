"""
Module: run_pipeline.py
Description: Master end-to-end ETL orchestrator:
1. Ingests and profiles raw datasets (extract.py)
2. Cleans each dataset independently into data/interim/ (clean.py)
3. Establishes anchor and performs attribute-based similarity matching into data/processed/student_master_wide.csv (stitch.py)
4. Decomposes wide table into Star Schema warehouse tables (load.py)
"""

import sys
import time
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

from src.etl.extract import load_raw_datasets, profile_datasets
from src.etl.clean import clean_all_datasets
from src.etl.stitch import stitch_datasets
from src.etl.fix_and_prepare import run_pipeline as run_fix_and_prepare
from src.etl.load import load_star_schema


def run_full_pipeline():
    """Runs the complete student data warehouse pipeline from raw files to star schema and model-ready splits."""
    start_time = time.time()
    print("\n" + "#" * 80)
    print("STARTING COMPLETE ETL, STITCHING & REMEDIATION PIPELINE")
    print("#" * 80 + "\n")

    # Step 1: Extract & Profile
    print(">>> STAGE 1: RAW DATA INGESTION & PROFILING")
    raw_datasets = load_raw_datasets()
    profile_datasets(raw_datasets)

    # Step 2: Clean independently
    print(">>> STAGE 2: INDEPENDENT DATASET CLEANING")
    cleaned_datasets = clean_all_datasets(raw_datasets)

    # Step 3: Anchor, Attribute-Based Matching & Master Wide Generation
    print(">>> STAGE 3: ATTRIBUTE-BASED STITCHING & MASTER WIDE GENERATION")
    wide_df = stitch_datasets()

    # Step 4: Fix, PII Removal, Label Engineering, & Train/Test Splits
    print(">>> STAGE 4: REMEDIATION, PII REMOVAL & MODEL PREPARATION")
    run_fix_and_prepare()
    # Reload wide_df to reflect post-remediation schema (116 columns including engineered features)
    wide_df = pd.read_csv(PROCESSED_DATA_DIR / "student_master_wide.csv")

    # Step 5: Star Schema Load
    print(">>> STAGE 5: STAR SCHEMA WAREHOUSE GENERATION")
    dim_student, fact_perf, fact_life, fact_career = load_star_schema()

    elapsed = time.time() - start_time
    print("#" * 80)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS")
    print("Processed Warehouse Artifacts (data/processed/):")
    print(f"  1. student_master_wide.csv       : {wide_df.shape[0]:,} rows x {wide_df.shape[1]} cols")
    print(f"  2. dim_student.csv               : {dim_student.shape[0]:,} rows x {dim_student.shape[1]} cols")
    print(f"  3. fact_performance.csv          : {fact_perf.shape[0]:,} rows x {fact_perf.shape[1]} cols")
    print(f"  4. fact_lifestyle.csv            : {fact_life.shape[0]:,} rows x {fact_life.shape[1]} cols")
    print(f"  5. fact_career.csv               : {fact_career.shape[0]:,} rows x {fact_career.shape[1]} cols")
    print(f"  6. model1_performance_train/test : 20,000 / 5,000 rows")
    print(f"  7. model2_atrisk_train/test      : 20,000 / 5,000 rows")
    print(f"  8. warehouse.db                  : SQLite database with 4 star schema tables")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    run_full_pipeline()
