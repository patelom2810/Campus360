"""
Module: extract.py
Project: KDAC-3 Analytics Platform
Purpose: Ingests all 6 raw departmental CSV source files from data/raw/,
         validating file presence, logging exact row counts, and capturing schemas.
"""

import sys
from pathlib import Path
from typing import Dict
import pandas as pd

# Ensure base directory is on path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import RAW_DATA_DIR, RAW_DATASET_MAPPING


def extract_all_sources(raw_dir: Path = RAW_DATA_DIR) -> Dict[str, pd.DataFrame]:
    """
    Extracts all 6 CSV sources as-is without modification.
    Logs row counts, column counts, and detects file existence.
    """
    raw_dfs = {}
    
    for filename in RAW_DATASET_MAPPING.keys():
        filepath = raw_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"[EXTRACT ERROR] Expected raw dataset not found: {filepath}")
            
        df = pd.read_csv(filepath)
        raw_dfs[filename] = df
        print(f"[EXTRACT] Loaded {filename:<25} — {len(df):>6} rows, {len(df.columns):>2} columns")
        
    return raw_dfs


if __name__ == "__main__":
    print("--- Running Extract Stage Independently ---")
    dfs = extract_all_sources()
    print(f"[EXTRACT] Completed extracting {len(dfs)} raw datasets.")
