"""
Module: transform.py
Project: KDAC-3 Analytics Platform
Purpose: Full transformation, cleaning, ID standardization, anomaly handling,
         and key-based stitching across all 6 departmental sources.
"""

import sys
import re
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import PROCESSED_DATA_DIR, RAW_DATASET_MAPPING


def clean_percentage(val) -> float:
    """Standardizes string percentages ('84.5%') or decimals (0.845) to float 84.5."""
    if pd.isna(val):
        return np.nan
    s_val = str(val).strip()
    if s_val.endswith("%"):
        try:
            return float(s_val.replace("%", "").strip())
        except ValueError:
            return np.nan
    try:
        f_val = float(s_val)
        # If expressed as decimal fraction <= 1.0 (e.g. 0.845), scale to percentage 84.5
        if 0.0 < f_val <= 1.0:
            return round(f_val * 100.0, 2)
        return round(f_val, 2)
    except ValueError:
        return np.nan


def clean_date_to_iso(val) -> str:
    """Parses mixed date strings (YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY, timestamps) into standard ISO YYYY-MM-DD."""
    if pd.isna(val):
        return None
    try:
        dt = pd.to_datetime(val, errors="coerce", format="mixed")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
        return None
    except Exception:
        return None


def clean_timestamp_to_iso(val) -> str:
    """Parses mixed datetime strings into ISO format YYYY-MM-DD HH:MM:SS."""
    if pd.isna(val):
        return None
    try:
        dt = pd.to_datetime(val, errors="coerce", format="mixed")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return None
    except Exception:
        return None


def transform_and_stitch(raw_dfs: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Transforms and cleans each raw source dataset:
      - Normalizes identifier columns to 'student_id'
      - Strips whitespace and standardizes format
      - Normalizes types (percentages, dates, casing)
      - Resolves anomalies and imputes missing values
      - Deduplicates on student_id
      - Stitches into master table and prepares warehouse relational tables
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. Transform: 1_student_records.csv
    # -------------------------------------------------------------
    print("[TRANSFORM] Processing 1_student_records.csv...")
    df1 = raw_dfs["1_student_records.csv"].copy()
    
    # Normalize ID
    df1.rename(columns={"student_id": "student_id"}, inplace=True)
    df1["student_id"] = df1["student_id"].astype(str).str.strip().str.upper()
    
    # Deduplicate
    initial_rows = len(df1)
    df1.drop_duplicates(subset=["student_id"], keep="first", inplace=True)
    print(f"[TRANSFORM] Standardized student IDs & removed {initial_rows - len(df1)} duplicate rows in 1_student_records")
    
    # Standardize enrollment_date
    df1["enrollment_date"] = df1["enrollment_date"].apply(clean_date_to_iso)
    
    # Anomaly checks: CGPA <= 10.0
    cgpa_anom = (df1["cgpa"] > 10.0) | (df1["cgpa"] < 0.0)
    if cgpa_anom.sum() > 0:
        median_cgpa = df1.loc[~cgpa_anom, "cgpa"].median()
        df1.loc[cgpa_anom, "cgpa"] = median_cgpa
        print(f"[TRANSFORM] Fixed {cgpa_anom.sum()} out-of-range CGPA anomalies (reset to median: {median_cgpa})")
        
    # Impute missing family_income_lpa
    if df1["family_income_lpa"].isna().sum() > 0:
        med_income = round(df1["family_income_lpa"].median(), 2)
        df1["family_income_lpa"] = df1["family_income_lpa"].fillna(med_income)
        print(f"[TRANSFORM] Imputed missing family_income_lpa with median ({med_income})")
        
    df1["cgpa"] = df1["cgpa"].round(2)
    df1["family_income_lpa"] = df1["family_income_lpa"].round(2)
    df1["backlogs"] = df1["backlogs"].fillna(0).astype(int)
    df1["failed_subjects"] = df1["failed_subjects"].fillna(0).astype(int)
    df1["at_risk_flag"] = df1["at_risk_flag"].fillna(0).astype(int)
    
    # Warehouse table 1: students
    students_df = df1[["student_id", "enrollment_date", "family_income_lpa", "cgpa", "backlogs", "failed_subjects", "at_risk_flag"]].copy()
    
    # -------------------------------------------------------------
    # 2. Transform: 2_exam_marks.csv
    # -------------------------------------------------------------
    print("[TRANSFORM] Processing 2_exam_marks.csv...")
    df2 = raw_dfs["2_exam_marks.csv"].copy()
    
    # Standardize StudentID -> student_id
    df2.rename(columns={"StudentID": "student_id"}, inplace=True)
    df2["student_id"] = df2["student_id"].astype(str).str.strip().str.upper()
    
    # Deduplicate
    init2 = len(df2)
    df2.drop_duplicates(subset=["student_id"], keep="first", inplace=True)
    print(f"[TRANSFORM] Standardized 'StudentID' -> 'student_id' & removed {init2 - len(df2)} duplicates in 2_exam_marks")
    
    # Clean percentage strings in previous_semester_percentage
    df2["previous_semester_percentage"] = df2["previous_semester_percentage"].apply(clean_percentage)
    
    # Anomaly checks: lowest_subject_score >= 0
    neg_scores = df2["lowest_subject_score"] < 0
    if neg_scores.sum() > 0:
        df2.loc[neg_scores, "lowest_subject_score"] = 0.0
        print(f"[TRANSFORM] Fixed {neg_scores.sum()} negative lowest_subject_score records (clipped to 0.0)")
        
    # Anomaly checks: previous_cgpa <= 10.0
    prev_cgpa_anom = (df2["previous_cgpa"] > 10.0) | (df2["previous_cgpa"] < 0.0)
    if prev_cgpa_anom.sum() > 0:
        med_pcgpa = df2.loc[~prev_cgpa_anom, "previous_cgpa"].median()
        df2.loc[prev_cgpa_anom, "previous_cgpa"] = med_pcgpa
        print(f"[TRANSFORM] Fixed {prev_cgpa_anom.sum()} previous_cgpa anomalies (reset to median: {med_pcgpa})")
        
    # Impute missing marks
    for col in ["previous_assignment_score", "practice_questions", "previous_semester_percentage"]:
        if df2[col].isna().sum() > 0:
            med = df2[col].median()
            df2[col] = df2[col].fillna(med)
            print(f"[TRANSFORM] Imputed missing {col} with median ({med})")
            
    df2["practice_questions"] = df2["practice_questions"].astype(int)
    
    # Warehouse table 2: academic_records
    academic_df = df2[[
        "student_id", "previous_cgpa", "previous_semester_percentage",
        "previous_subject_avg", "weak_subject_count", "subject_consistency",
        "performance_band"
    ]].copy()
    
    # Warehouse table 3: exam_marks
    exam_df = df2[[
        "student_id", "previous_internal_marks", "previous_assignment_score",
        "previous_midterm_score", "lowest_subject_score",
        "assignment_completion_rate", "practice_questions",
        "next_semester_marks"
    ]].copy()
    
    # -------------------------------------------------------------
    # 3. Transform: 3_attendance.csv
    # -------------------------------------------------------------
    print("[TRANSFORM] Processing 3_attendance.csv...")
    df3 = raw_dfs["3_attendance.csv"].copy()
    
    # Standardize roll_no -> student_id
    df3.rename(columns={"roll_no": "student_id"}, inplace=True)
    df3["student_id"] = df3["student_id"].astype(str).str.strip().str.upper()
    
    # Deduplicate
    init3 = len(df3)
    df3.drop_duplicates(subset=["student_id"], keep="first", inplace=True)
    print(f"[TRANSFORM] Standardized 'roll_no' -> 'student_id' & removed {init3 - len(df3)} duplicates in 3_attendance")
    
    # Clean attendance_percentage string/decimal
    df3["attendance_percentage"] = df3["attendance_percentage"].apply(clean_percentage)
    
    # Out of range attendance > 100.0 clipped to 100.0
    high_att = df3["attendance_percentage"] > 100.0
    if high_att.sum() > 0:
        df3.loc[high_att, "attendance_percentage"] = 100.0
        print(f"[TRANSFORM] Clipped {high_att.sum()} out-of-range attendance percentages (> 100%) to 100.0%")
        
    # Impute missing self_learning_hours
    if df3["self_learning_hours"].isna().sum() > 0:
        med_sl = round(df3["self_learning_hours"].median(), 2)
        df3["self_learning_hours"] = df3["self_learning_hours"].fillna(med_sl)
        print(f"[TRANSFORM] Imputed missing self_learning_hours with median ({med_sl})")
        
    df3["last_sync_time"] = df3["last_sync_time"].apply(clean_timestamp_to_iso)
    
    # Warehouse table 4: attendance
    attendance_df = df3[[
        "student_id", "attendance_percentage", "study_hours_daily",
        "self_learning_hours", "study_hours_per_week", "last_sync_time"
    ]].copy()
    
    # -------------------------------------------------------------
    # 4. Transform: 4_lifestyle.csv
    # -------------------------------------------------------------
    print("[TRANSFORM] Processing 4_lifestyle.csv...")
    df4 = raw_dfs["4_lifestyle.csv"].copy()
    
    df4["student_id"] = df4["student_id"].astype(str).str.strip().str.upper()
    init4 = len(df4)
    df4.drop_duplicates(subset=["student_id"], keep="first", inplace=True)
    print(f"[TRANSFORM] Standardized student IDs & removed {init4 - len(df4)} duplicates in 4_lifestyle")
    
    # Anomaly checks: sleep_hours between 0 and 24
    sleep_anom = (df4["sleep_hours"] > 24.0) | (df4["sleep_hours"] < 0.0)
    if sleep_anom.sum() > 0:
        med_sleep = round(df4.loc[~sleep_anom, "sleep_hours"].median(), 2)
        df4.loc[sleep_anom, "sleep_hours"] = med_sleep
        print(f"[TRANSFORM] Fixed {sleep_anom.sum()} invalid sleep hours (reset to median: {med_sleep})")
        
    # Anomaly checks: gaming_hours >= 0
    gaming_anom = df4["gaming_hours"] < 0.0
    if gaming_anom.sum() > 0:
        df4.loc[gaming_anom, "gaming_hours"] = 0.0
        print(f"[TRANSFORM] Fixed {gaming_anom.sum()} negative gaming hours (clipped to 0.0)")
        
    # Impute missing values
    for col in ["screen_time", "gym_frequency"]:
        if df4[col].isna().sum() > 0:
            med_val = df4[col].median()
            df4[col] = df4[col].fillna(med_val)
            print(f"[TRANSFORM] Imputed missing {col} with median ({med_val})")
            
    df4["gym_frequency"] = df4["gym_frequency"].astype(int)
    df4["survey_date"] = df4["survey_date"].apply(clean_date_to_iso)
    
    # Warehouse table 5: lifestyle
    lifestyle_df = df4[[
        "student_id", "sleep_hours", "screen_time", "gaming_hours",
        "stress_level", "burnout_score", "motivation_level", "adaptability_score",
        "gym_frequency", "wellness_score", "screen_to_study_ratio",
        "extracurricular_hours", "survey_date"
    ]].copy()
    
    # -------------------------------------------------------------
    # 5. Transform: 5_skills.csv
    # -------------------------------------------------------------
    print("[TRANSFORM] Processing 5_skills.csv...")
    df5 = raw_dfs["5_skills.csv"].copy()
    
    # Standardize STUDENT_ID -> student_id
    df5.rename(columns={"STUDENT_ID": "student_id"}, inplace=True)
    df5["student_id"] = df5["student_id"].astype(str).str.strip().str.upper()
    
    init5 = len(df5)
    df5.drop_duplicates(subset=["student_id"], keep="first", inplace=True)
    print(f"[TRANSFORM] Standardized 'STUDENT_ID' -> 'student_id' & removed {init5 - len(df5)} duplicates in 5_skills")
    
    # Clean numeric fields with string noise
    for col in ["resume_score", "communication_skills", "aptitude_score", "mock_interview_score"]:
        df5[col] = pd.to_numeric(df5[col].astype(str).str.strip(), errors="coerce")
        if df5[col].isna().sum() > 0:
            med_s = round(df5[col].median(), 2)
            df5[col] = df5[col].fillna(med_s)
            print(f"[TRANSFORM] Imputed missing {col} with median ({med_s})")
            
    for int_col in ["development_projects_count", "ai_ml_projects", "git_hub_repos"]:
        df5[int_col] = df5[int_col].fillna(0).astype(int)
        
    # Warehouse table 6: skills
    skills_df = df5[[
        "student_id", "resume_score", "communication_skills", "aptitude_score",
        "mock_interview_score", "development_projects_count", "ai_ml_projects",
        "git_hub_repos", "ai_tool_usage_frequency", "prompt_engineering_skill"
    ]].copy()
    
    # -------------------------------------------------------------
    # 6. Transform: 6_career_preferences.csv
    # -------------------------------------------------------------
    print("[TRANSFORM] Processing 6_career_preferences.csv...")
    df6 = raw_dfs["6_career_preferences.csv"].copy()
    
    # Standardize roll_number -> student_id
    df6.rename(columns={"roll_number": "student_id"}, inplace=True)
    df6["student_id"] = df6["student_id"].astype(str).str.strip().str.upper()
    
    init6 = len(df6)
    df6.drop_duplicates(subset=["student_id"], keep="first", inplace=True)
    print(f"[TRANSFORM] Standardized 'roll_number' -> 'student_id' & removed {init6 - len(df6)} duplicates in 6_career_preferences")
    
    # Standardize casing in career_goal ('job' -> 'Job', 'HIGHER STUDIES' -> 'Higher Studies')
    df6["career_goal"] = df6["career_goal"].astype(str).str.strip().str.title()
    # Map title-case variations to canonical
    goal_mapping = {
        "Job": "Job",
        "Higher Studies": "Higher Studies",
        "Startup/Entrepreneurship": "Startup/Entrepreneurship",
        "Startup": "Startup/Entrepreneurship",
        "Entrepreneurship": "Startup/Entrepreneurship"
    }
    df6["career_goal"] = df6["career_goal"].map(goal_mapping).fillna("Job")
    
    # Standardize preferred_domain
    if df6["preferred_domain"].isna().sum() > 0:
        mode_domain = df6["preferred_domain"].mode()[0]
        df6["preferred_domain"] = df6["preferred_domain"].fillna(mode_domain)
        print(f"[TRANSFORM] Imputed missing preferred_domain with mode ('{mode_domain}')")
        
    df6["submitted_at"] = df6["submitted_at"].apply(clean_timestamp_to_iso)
    df6["hackathons_participated"] = df6["hackathons_participated"].fillna(0).astype(int)
    
    # Warehouse table 7: career_preferences
    career_df = df6[["student_id", "hackathons_participated", "preferred_domain", "career_goal", "submitted_at"]].copy()
    
    # -------------------------------------------------------------
    # 7. Stitch All Clean Datasets on student_id
    # -------------------------------------------------------------
    print("\n[STITCH] Executing key-based join across all 6 standardized datasets on 'student_id'...")
    
    master_df = students_df.merge(academic_df, on="student_id", how="inner") \
                           .merge(exam_df, on="student_id", how="inner") \
                           .merge(attendance_df, on="student_id", how="inner") \
                           .merge(lifestyle_df, on="student_id", how="inner") \
                           .merge(skills_df, on="student_id", how="inner") \
                           .merge(career_df, on="student_id", how="inner")
                           
    match_rate = (len(master_df) / len(students_df)) * 100.0
    print(f"[STITCH] Successfully stitched {len(master_df):,} students across all 6 sources (Match Rate: {match_rate:.1f}%)")
    
    # Save processed files
    master_path = PROCESSED_DATA_DIR / "student_master_stitched.csv"
    master_df.to_csv(master_path, index=False)
    print(f"[TRANSFORM] Saved stitched master dataset to: {master_path.name} ({master_df.shape[0]} rows, {master_df.shape[1]} cols)")
    
    warehouse_dfs = {
        "students": students_df,
        "academic_records": academic_df,
        "exam_marks": exam_df,
        "attendance": attendance_df,
        "lifestyle": lifestyle_df,
        "skills": skills_df,
        "career_preferences": career_df
    }
    
    for tbl_name, df_tbl in warehouse_dfs.items():
        tbl_path = PROCESSED_DATA_DIR / f"cleaned_{tbl_name}.csv"
        df_tbl.to_csv(tbl_path, index=False)
        
    print(f"[TRANSFORM] Saved all {len(warehouse_dfs)} cleaned relational warehouse tables to data/processed/")
    return warehouse_dfs, master_df


if __name__ == "__main__":
    from etl.extract import extract_all_sources
    print("--- Running Transform & Stitch Stage Independently ---")
    raws = extract_all_sources()
    tbls, master = transform_and_stitch(raws)
    print(f"[TRANSFORM] Done. Stitched master shape: {master.shape}")
