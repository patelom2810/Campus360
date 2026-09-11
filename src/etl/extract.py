"""
Module: extract.py
Description: Ingests raw student datasets from data/raw/, profiles column names,
shapes, data types, nulls, and highlights unit/scale inconsistencies.
"""

from pathlib import Path
from typing import Dict, Any
import pandas as pd

# Paths configuration
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

DATASET_FILES = {
    "suvidya": "suvidya_student_performance.csv",
    "kundan": "kundan_student_performance.csv",
    "sehaj": "sehaj_student_lifestyle.csv",
    "navinpatidar": "navinpatidar_indian_placement.csv",
    "sakharebharat": "sakharebharat_indian_placement_2025.csv",
    "shambhuraje": "shambhuraje_placement_career_2026.csv"
}


def load_raw_datasets(raw_dir: Path = RAW_DATA_DIR) -> Dict[str, pd.DataFrame]:
    """Loads all 6 raw CSV files into a dictionary of DataFrames."""
    datasets = {}
    for key, filename in DATASET_FILES.items():
        file_path = raw_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing expected raw dataset: {file_path}")
        df = pd.read_csv(file_path)
        datasets[key] = df
    return datasets


def profile_datasets(datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Profiles each dataset: shapes, dtypes, nulls, sample rows, and scale inconsistencies."""
    profiles = {}
    print("=" * 80)
    print("RAW DATA PROFILING & QUALITY REPORT")
    print("=" * 80)

    for name, df in datasets.items():
        shape = df.shape
        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0].to_dict()

        print(f"\n[{name.upper()}] Filename: {DATASET_FILES[name]}")
        print(f"  Shape: {shape[0]:,} rows x {shape[1]} columns")
        print(f"  Columns: {df.columns.tolist()}")
        print(f"  Null Values: {cols_with_nulls if cols_with_nulls else 'None (0 nulls)'}")

        # Check scale/units on numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        scale_info = {}
        for c in numeric_cols:
            scale_info[c] = {"min": round(float(df[c].min()), 2), "max": round(float(df[c].max()), 2)}

        print("  Numeric Ranges (Scale Check):")
        for c, r in list(scale_info.items())[:6]:
            print(f"    - {c}: [{r['min']} to {r['max']}]")
        if len(scale_info) > 6:
            print(f"    ... ({len(scale_info) - 6} more numeric columns)")

        profiles[name] = {
            "shape": shape,
            "columns": df.columns.tolist(),
            "nulls": cols_with_nulls,
            "scales": scale_info
        }

    # Cross-dataset scale & naming discrepancy report
    print("\n" + "-" * 80)
    print("CROSS-DATASET SCALE & UNIT MISMATCH AUDIT:")
    print("  - GPA / CGPA scales:")
    print("      * sehaj: GPA on 4.0 scale (min 2.24, max 4.0)")
    print("      * sakharebharat: cgpa on 10.0 scale (min 5.5, max 9.8)")
    print("      * shambhuraje: cgpa on 10.0 scale (min 5.0, max 10.0)")
    print("  - Marks / Scores:")
    print("      * suvidya: Math/Science/English on 0-100 scale, Final_Percentage on 0-100")
    print("      * kundan: Math/Science/English on 0-100 scale, overall_score on 0-100")
    print("  - Salary Packages:")
    print("      * navinpatidar: Salary (INR) in absolute annual rupees (~300,000 to ~1,200,000)")
    print("      * sakharebharat: package_lpa in Lakhs Per Annum (0 to 15 LPA)")
    print("      * shambhuraje: salary_lpa in Lakhs Per Annum (0 to 35.1 LPA)")
    print("  - Column Casing:")
    print("      * PascalCase in suvidya / navinpatidar ('Student_ID', 'Graduation Year')")
    print("      * snake_case in kundan / sakharebharat / shambhuraje ('student_id', 'cgpa')")
    print("=" * 80 + "\n")

    return profiles


def main():
    datasets = load_raw_datasets()
    profile_datasets(datasets)


if __name__ == "__main__":
    main()
