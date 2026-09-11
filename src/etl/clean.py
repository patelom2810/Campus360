"""
Module: clean.py
Description: Cleans each of the 6 datasets independently:
- Column standardisation (snake_case)
- Data type casting (numeric as float/int, categorical as category/object)
- Null value imputation (numeric with median, categorical with mode/Unknown)
- Value clipping (attendance <= 100%, valid scores, GPA ranges)
- Deduplication
Saves outputs to data/interim/<name>_clean.csv
"""

import re
import sys
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.etl.extract import load_raw_datasets
INTERIM_DATA_DIR = BASE_DIR / "data" / "interim"


def to_snake_case(name: str) -> str:
    """Converts any string to a clean snake_case identifier."""
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    # Handle camelCase / PascalCase
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return re.sub(r"_+", "_", s2)


def clean_suvidya(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Suvidya academic performance dataset (~5,000 rows)."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]
    
    # Avoid reserved word collision
    if "class" in df.columns:
        df = df.rename(columns={"class": "academic_class"})

    # Numeric clipping
    df["attendance_percentage"] = df["attendance_percentage"].clip(0.0, 100.0)
    for score_col in ["math_score", "science_score", "english_score", "previous_year_score", "final_percentage"]:
        if score_col in df.columns:
            df[score_col] = pd.to_numeric(df[score_col], errors="coerce").clip(0.0, 100.0)

    # Imputation if any
    for col in df.select_dtypes(include=["number"]).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    for col in df.select_dtypes(exclude=["number"]).columns:
        df[col] = df[col].astype(str).str.strip()
        if df[col].isnull().any() or (df[col] == "nan").any():
            mode_val = df[col].mode()[0]
            df[col] = df[col].replace("nan", mode_val).fillna(mode_val)

    # Standardize gender
    if "gender" in df.columns:
        df["gender"] = df["gender"].str.title()

    df = df.drop_duplicates().reset_index(drop=True)
    return df


def clean_kundan(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Kundan student performance dataset (25,000 rows)."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]

    # Numeric clipping
    df["attendance_percentage"] = df["attendance_percentage"].clip(0.0, 100.0)
    for score_col in ["math_score", "science_score", "english_score", "overall_score"]:
        if score_col in df.columns:
            df[score_col] = pd.to_numeric(df[score_col], errors="coerce").clip(0.0, 100.0)

    # Impute numeric with median
    for col in df.select_dtypes(include=["number"]).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    # String cleanup
    for col in df.select_dtypes(exclude=["number"]).columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
        if df[col].isnull().any():
            df[col] = df[col].fillna("unknown")

    # Standardize gender
    if "gender" in df.columns:
        df["gender"] = df["gender"].map({"male": "Male", "female": "Female", "other": "Other"}).fillna("Other")

    df = df.drop_duplicates().reset_index(drop=True)
    return df


def clean_sehaj(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Sehaj student lifestyle dataset (2,000 rows)."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]

    # Clip GPA to [0.0, 4.0]
    if "gpa" in df.columns:
        df["gpa"] = pd.to_numeric(df["gpa"], errors="coerce").clip(0.0, 4.0)

    # Clip hours
    for h_col in ["study_hours_per_day", "extracurricular_hours_per_day", "sleep_hours_per_day",
                  "social_hours_per_day", "physical_activity_hours_per_day"]:
        if h_col in df.columns:
            df[h_col] = pd.to_numeric(df[h_col], errors="coerce").clip(0.0, 24.0)

    # Stress level standardization
    if "stress_level" in df.columns:
        df["stress_level"] = df["stress_level"].astype(str).str.strip().str.title()

    # Impute if any
    for col in df.select_dtypes(include=["number"]).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    df = df.drop_duplicates().reset_index(drop=True)
    return df


def clean_navinpatidar(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Navinpatidar placement dataset (1,000 rows)."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]

    # Clean salary in INR and compute package_lpa
    if "salary_inr" in df.columns:
        df["salary_inr"] = pd.to_numeric(df["salary_inr"], errors="coerce").fillna(0)
        df["salary_lpa"] = (df["salary_inr"] / 100000.0).round(2)

    # Clean string columns
    for col in df.select_dtypes(exclude=["number"]).columns:
        df[col] = df[col].astype(str).str.strip()

    # All records in Navinpatidar have company & salary -> placed
    df["placement_status"] = "Placed"

    df = df.drop_duplicates().reset_index(drop=True)
    return df


def clean_sakharebharat(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Sakharebharat placement dataset 2025 (12,000 rows)."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]

    # Handle nulls in company_type:
    # Students with placed == 0 should have company_type = 'Not Placed'
    df["placed"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0).astype(int)
    
    unplaced_mask = df["placed"] == 0
    df.loc[unplaced_mask, "company_type"] = "Not Placed"
    # For remaining placed students with missing company_type, impute mode
    placed_mode = df.loc[~unplaced_mask, "company_type"].mode()
    mode_val = placed_mode[0] if not placed_mode.empty else "Service"
    df["company_type"] = df["company_type"].fillna(mode_val)

    # Numeric clipping
    df["cgpa"] = pd.to_numeric(df["cgpa"], errors="coerce").clip(0.0, 10.0)
    df["aptitude_score"] = pd.to_numeric(df["aptitude_score"], errors="coerce").clip(0.0, 100.0)
    df["package_lpa"] = pd.to_numeric(df["package_lpa"], errors="coerce").clip(0.0, 100.0)
    df["coding_skills"] = pd.to_numeric(df["coding_skills"], errors="coerce").clip(0.0, 10.0)
    df["communication_skills"] = pd.to_numeric(df["communication_skills"], errors="coerce").clip(0.0, 10.0)

    # Impute numeric with median
    for col in df.select_dtypes(include=["number"]).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    if "gender" in df.columns:
        df["gender"] = df["gender"].astype(str).str.strip().str.title()

    df = df.drop_duplicates().reset_index(drop=True)
    return df


def clean_shambhuraje(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Shambhuraje placement and career success dataset 2026 (25,000 rows - Anchor)."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]

    # Handle specific nulls documented in extraction:
    # github_repos, mock_interview_score, sleep_hours
    for num_col in ["github_repos", "mock_interview_score", "sleep_hours"]:
        if num_col in df.columns and df[num_col].isnull().any():
            median_val = df[num_col].median()
            df[num_col] = df[num_col].fillna(median_val)

    # company_type and work_mode nulls
    if "company_type" in df.columns:
        not_placed_mask = df["placement_status"].astype(str).str.lower() != "placed"
        df.loc[not_placed_mask & df["company_type"].isnull(), "company_type"] = "Not Placed"
        mode_company = df["company_type"].mode()[0] if not df["company_type"].mode().empty else "Product-Based"
        df["company_type"] = df["company_type"].fillna(mode_company)

    if "work_mode" in df.columns:
        not_placed_mask = df["placement_status"].astype(str).str.lower() != "placed"
        df.loc[not_placed_mask & df["work_mode"].isnull(), "work_mode"] = "None"
        mode_work = df["work_mode"].mode()[0] if not df["work_mode"].mode().empty else "Onsite"
        df["work_mode"] = df["work_mode"].fillna(mode_work)

    # Impute any remaining numeric columns with median
    for col in df.select_dtypes(include=["number"]).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    # Impute remaining categorical with mode
    for col in df.select_dtypes(exclude=["number"]).columns:
        if df[col].isnull().any():
            mode_val = df[col].mode()[0]
            df[col] = df[col].fillna(mode_val)

    # Range clippings
    if "cgpa" in df.columns:
        df["cgpa"] = df["cgpa"].clip(0.0, 10.0)
    if "attendance_percentage" in df.columns:
        df["attendance_percentage"] = df["attendance_percentage"].clip(0.0, 100.0)
    for score_col in ["resume_score", "communication_skills", "aptitude_score", "mock_interview_score",
                      "stress_level", "burnout_score", "motivation_level", "layoffs_risk_score",
                      "ai_tool_usage_frequency", "prompt_engineering_skill", "ai_fear_score", "adaptability_score"]:
        if score_col in df.columns:
            df[score_col] = df[score_col].clip(0.0, 100.0)

    if "gender" in df.columns:
        df["gender"] = df["gender"].astype(str).str.strip().str.title()

    df = df.drop_duplicates().reset_index(drop=True)
    return df


def clean_all_datasets(raw_datasets: Dict[str, pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
    """Runs cleaning functions for all datasets and writes outputs to data/interim/."""
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if raw_datasets is None:
        raw_datasets = load_raw_datasets()

    cleaning_handlers = {
        "suvidya": clean_suvidya,
        "kundan": clean_kundan,
        "sehaj": clean_sehaj,
        "navinpatidar": clean_navinpatidar,
        "sakharebharat": clean_sakharebharat,
        "shambhuraje": clean_shambhuraje
    }

    cleaned_datasets = {}
    print("=" * 80)
    print("CLEANING & PREPROCESSING PIPELINE (data/interim/)")
    print("=" * 80)

    for name, handler in cleaning_handlers.items():
        df_raw = raw_datasets[name]
        df_clean = handler(df_raw)
        out_filename = f"{name}_student_performance_clean.csv" if "performance" in name else f"{name}_clean.csv"
        # Standard naming convention
        save_name = f"{name}_clean.csv"
        out_path = INTERIM_DATA_DIR / save_name
        df_clean.to_csv(out_path, index=False)
        cleaned_datasets[name] = df_clean

        nulls_after = df_clean.isnull().sum().sum()
        print(f"[{name.upper()}] Cleaned:")
        print(f"  Saved to: {out_path.name}")
        print(f"  Shape: {df_clean.shape[0]:,} rows x {df_clean.shape[1]} cols")
        print(f"  Total remaining nulls: {nulls_after}")

    print("=" * 80 + "\n")
    return cleaned_datasets


def main():
    clean_all_datasets()


if __name__ == "__main__":
    main()
