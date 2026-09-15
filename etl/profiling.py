"""
Module: profiling.py
Purpose: In-depth exploratory data profiling of all raw CSV datasets in data/raw/.
Generates:
  1. Detailed per-file metrics (schema, nulls, duplicates, outliers, types)
  2. Student ID reconciliation report across all 6 files
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure root directory is on sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import RAW_DATA_DIR, RAW_DATASET_MAPPING


def profile_raw_datasets():
    print("=" * 80)
    print("      KDAC-3 DATA ENGINEERING LAYER — PHASE 1: DATA PROFILING REPORT      ")
    print("=" * 80)
    
    reports = {}
    id_sets = {}
    
    for filename, id_col in RAW_DATASET_MAPPING.items():
        filepath = RAW_DATA_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Raw dataset not found: {filepath}")
            
        df = pd.read_csv(filepath)
        
        n_rows, n_cols = df.shape
        unique_students = df[id_col].nunique()
        duplicate_rows = df.duplicated().sum()
        duplicate_ids = df.duplicated(subset=[id_col]).sum()
        
        # Null values
        null_counts = df.isna().sum()
        cols_with_nulls = null_counts[null_counts > 0].to_dict()
        
        # Data types
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
        
        # Target / leakage detection
        targets_found = [c for c in df.columns if c in ["next_semester_marks", "performance_band", "at_risk_flag"]]
        
        # Store student IDs for cross-dataset comparison
        id_sets[filename] = set(df[id_col].dropna().astype(str).str.strip().unique())
        
        reports[filename] = {
            "rows": n_rows,
            "cols": n_cols,
            "id_col": id_col,
            "unique_students": unique_students,
            "duplicate_rows": duplicate_rows,
            "duplicate_ids": duplicate_ids,
            "cols_with_nulls": cols_with_nulls,
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
            "targets_found": targets_found,
            "columns": list(df.columns)
        }
        
        print(f"\n📁 FILE: {filename}")
        print(f"   • Rows: {n_rows:,} | Columns: {n_cols} | Size: {filepath.stat().st_size / 1024:.1f} KB")
        print(f"   • Student ID Column: '{id_col}'")
        print(f"   • Unique Students: {unique_students:,} | Duplicate IDs: {duplicate_ids} | Exact Duplicate Rows: {duplicate_rows}")
        if cols_with_nulls:
            null_str = ", ".join([f"{c}: {cnt} ({cnt/n_rows*100:.1f}%)" for c, cnt in cols_with_nulls.items()])
            print(f"   • Missing Values: {null_str}")
        else:
            print(f"   • Missing Values: None")
        print(f"   • Numeric Columns ({len(numeric_cols)}): {numeric_cols}")
        print(f"   • Categorical Columns ({len(categorical_cols)}): {categorical_cols}")
        if targets_found:
            print(f"   • Target / Sensitive Leakage Columns: {targets_found}")
            
    # Cross-dataset student ID comparison
    print("\n" + "=" * 80)
    print("      KDAC-3 DATA ENGINEERING LAYER — PHASE 2: ID RECONCILIATION REPORT     ")
    print("=" * 80)
    
    all_unique_ids = set().union(*id_sets.values())
    intersection_ids = set.intersection(*id_sets.values())
    
    print(f"Total Master Unique IDs Across All Datasets: {len(all_unique_ids):,}")
    print(f"IDs Present in ALL 6 Datasets: {len(intersection_ids):,}")
    print("\nDetailed Reconciliation Matrix:")
    print(f"{'Dataset':<28} | {'Total Rows':<10} | {'Unique IDs':<10} | {'Matched IDs':<11} | {'Unmatched IDs':<13} | {'Match Rate'}")
    print("-" * 90)
    
    for filename, id_set in id_sets.items():
        total_rows = reports[filename]["rows"]
        unique_cnt = len(id_set)
        matched_cnt = len(id_set.intersection(intersection_ids))
        unmatched_cnt = unique_cnt - matched_cnt
        match_rate = (matched_cnt / len(all_unique_ids)) * 100
        print(f"{filename:<28} | {total_rows:<10} | {unique_cnt:<10} | {matched_cnt:<11} | {unmatched_cnt:<13} | {match_rate:.1f}%")
        
    print("=" * 80)
    return reports, id_sets


if __name__ == "__main__":
    profile_raw_datasets()
