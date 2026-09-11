"""
Module: load.py
Description: Implements Step 6 of the project architecture:
Splits data/processed/student_master_wide.csv into a Star Schema:
  1. dim_student.csv: Demographics & background dimension (25,000 rows)
  2. fact_performance.csv: Subject-level marks and attendance fact table (long format)
  3. fact_lifestyle.csv: Habit, sleep, stress, and wellness fact table (25,000 rows)
  4. fact_career.csv: Skills, internships, backlogs, placement status & salary facts (25,000 rows)

Loads data warehouse tables into PostgreSQL (via SQLAlchemy & psycopg2) with:
  - Explicit column dtypes (VARCHAR, Float, Integer)
  - Primary Key on dim_student(student_id)
  - Foreign Key constraints on fact_performance, fact_lifestyle, fact_career referencing dim_student(student_id)
  - Automated row count validation matching source CSVs exactly
  - Local SQLite fallback support via DB_ENGINE (postgres | sqlite)
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import Engine

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Load environment variables
load_dotenv(BASE_DIR / ".env")


def get_db_url(engine_type: Optional[str] = None) -> str:
    """Returns the database URL based on the DB_ENGINE environment variable."""
    db_engine = engine_type or os.getenv("DB_ENGINE", "postgres").lower()
    if db_engine == "sqlite":
        sqlite_path = PROCESSED_DATA_DIR / "warehouse.db"
        return f"sqlite:///{sqlite_path.as_posix()}"
    
    # PostgreSQL URL
    return os.getenv(
        "DATABASE_URL",
        "postgresql://campus360:changeme@localhost:5432/campus360_warehouse"
    )


def create_warehouse_engine(engine_type: Optional[str] = None) -> Tuple[Engine, str]:
    """
    Creates and returns a SQLAlchemy engine along with the active engine name.
    Falls back gracefully to SQLite if PostgreSQL connection fails.
    """
    selected_engine = (engine_type or os.getenv("DB_ENGINE", "postgres")).lower()
    
    if selected_engine == "postgres":
        pg_url = get_db_url("postgres")
        try:
            engine = sqlalchemy.create_engine(pg_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return engine, "postgres"
        except Exception as err:
            print(f"[WARNING] PostgreSQL connection failed ({err}). Falling back to SQLite.")
            selected_engine = "sqlite"

    sqlite_url = get_db_url("sqlite")
    engine = sqlalchemy.create_engine(sqlite_url)
    return engine, "sqlite"


def build_dim_student(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Builds dim_student dimension table (25,000 rows)."""
    dim_student = pd.DataFrame({
        "student_id": wide_df["student_id"],
        "gender": wide_df["anchor_gender"],
        "age": wide_df["anchor_age"],
        "stream_branch": wide_df["anchor_branch"],
        "degree": wide_df["anchor_degree"],
        "college_tier": wide_df["anchor_college_tier"],
        "city_tier": wide_df["anchor_city_tier"],
        "state": wide_df["anchor_state"],
        "family_income_lpa": wide_df["anchor_family_income_lpa"]
    })
    return dim_student


def build_fact_performance(wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds fact_performance in clean normalized long format:
    student_id, source, assessment_term, subject, marks, max_marks, attendance_pct, grade_or_status
    """
    records = []

    # 1. Suvidya records (Math, Science, English, Final)
    suvidya_mask = wide_df["has_suvidya_match"] == 1
    suv_df = wide_df[suvidya_mask]
    for _, row in suv_df.iterrows():
        sid = row["student_id"]
        att = row["suvidya_attendance_percentage"]
        pf = row["suvidya_pass_fail"]
        records.append({
            "student_id": sid,
            "source": "Suvidya",
            "assessment_term": "Term Exam",
            "subject": "Mathematics",
            "marks": row["suvidya_math_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": pf
        })
        records.append({
            "student_id": sid,
            "source": "Suvidya",
            "assessment_term": "Term Exam",
            "subject": "Science",
            "marks": row["suvidya_science_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": pf
        })
        records.append({
            "student_id": sid,
            "source": "Suvidya",
            "assessment_term": "Term Exam",
            "subject": "English",
            "marks": row["suvidya_english_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": pf
        })
        records.append({
            "student_id": sid,
            "source": "Suvidya",
            "assessment_term": "Annual Final",
            "subject": "Overall Percentage",
            "marks": row["suvidya_final_percentage"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": row["suvidya_performance_level"]
        })

    # 2. Kundan records (Math, Science, English, Overall)
    kundan_mask = wide_df["has_kundan_match"] == 1
    kun_df = wide_df[kundan_mask]
    for _, row in kun_df.iterrows():
        sid = row["student_id"]
        att = row["kundan_attendance_percentage"]
        fg = row["kundan_final_grade"]
        records.append({
            "student_id": sid,
            "source": "Kundan",
            "assessment_term": "Term Exam",
            "subject": "Mathematics",
            "marks": row["kundan_math_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": fg
        })
        records.append({
            "student_id": sid,
            "source": "Kundan",
            "assessment_term": "Term Exam",
            "subject": "Science",
            "marks": row["kundan_science_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": fg
        })
        records.append({
            "student_id": sid,
            "source": "Kundan",
            "assessment_term": "Term Exam",
            "subject": "English",
            "marks": row["kundan_english_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": fg
        })
        records.append({
            "student_id": sid,
            "source": "Kundan",
            "assessment_term": "Annual Final",
            "subject": "Overall Score",
            "marks": row["kundan_overall_score"],
            "max_marks": 100.0,
            "attendance_pct": att,
            "grade_or_status": fg
        })

    # 3. Anchor CGPA summary record for every student
    for _, row in wide_df.iterrows():
        records.append({
            "student_id": row["student_id"],
            "source": "Master Anchor (Shambhuraje)",
            "assessment_term": "Cumulative Degree",
            "subject": "Degree CGPA",
            "marks": row["anchor_cgpa"],
            "max_marks": 10.0,
            "attendance_pct": row["anchor_attendance_percentage"],
            "grade_or_status": "Passed" if row["anchor_cgpa"] >= 5.0 else "Arrear"
        })

    fact_perf = pd.DataFrame(records)
    return fact_perf


def build_fact_lifestyle(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Builds fact_lifestyle fact table (25,000 rows)."""
    fact_lifestyle = pd.DataFrame({
        "student_id": wide_df["student_id"],
        "sleep_hours": wide_df["anchor_sleep_hours"].round(1),
        "screen_time_hours": wide_df["anchor_screen_time"].round(1),
        "gaming_hours": wide_df["anchor_gaming_hours"].round(1),
        "study_hours_daily": wide_df["anchor_study_hours_daily"].round(1),
        "stress_level": wide_df["anchor_stress_level"],
        "burnout_score": wide_df["anchor_burnout_score"],
        "gym_frequency_per_week": wide_df["anchor_gym_frequency"],
        "motivation_level": wide_df["anchor_motivation_level"],
        "physical_activity_hours_sehaj": wide_df["sehaj_physical_activity_hours_per_day"],
        "stress_level_sehaj": wide_df["sehaj_stress_level"]
    })

    # Derive lifestyle risk flag
    high_risk_condition = (
        (fact_lifestyle["sleep_hours"] < 5.0) |
        (fact_lifestyle["stress_level"] > 75) |
        (fact_lifestyle["burnout_score"] > 75)
    )
    fact_lifestyle["lifestyle_risk_flag"] = high_risk_condition.map({True: "High Risk", False: "Normal"})
    return fact_lifestyle


def build_fact_career(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Builds fact_career fact table (25,000 rows)."""
    fact_career = pd.DataFrame({
        "student_id": wide_df["student_id"],
        "cgpa": wide_df["anchor_cgpa"],
        "backlogs": wide_df["anchor_backlog_history"],
        "internships": wide_df["anchor_internships_completed"],
        "dsa_problems_solved": wide_df["anchor_dsa_problems_solved"],
        "github_repos": wide_df["anchor_git_hub_repos"],
        "coding_skills_sakhare": wide_df["sakhare_coding_skills"],
        "communication_skills": wide_df["anchor_communication_skills"],
        "aptitude_score": wide_df["anchor_aptitude_score"],
        "mock_interview_score": wide_df["anchor_mock_interview_score"],
        "placement_status": wide_df["anchor_placement_status"],
        "company_type": wide_df["anchor_company_type"],
        "work_mode": wide_df["anchor_work_mode"],
        "salary_lpa": wide_df["anchor_salary_lpa"],
        "offer_count": wide_df["anchor_offer_count"],
        "layoffs_risk_score": wide_df["anchor_layoffs_risk_score"]
    })
    return fact_career


def get_table_dtypes() -> Dict[str, Dict]:
    """Returns explicit SQLAlchemy column dtype mappings to ensure strict typing in PostgreSQL."""
    dim_dtypes = {
        "student_id": sqlalchemy.types.VARCHAR(16),
        "gender": sqlalchemy.types.VARCHAR(16),
        "age": sqlalchemy.types.Integer(),
        "stream_branch": sqlalchemy.types.VARCHAR(64),
        "degree": sqlalchemy.types.VARCHAR(32),
        "college_tier": sqlalchemy.types.Integer(),
        "city_tier": sqlalchemy.types.Integer(),
        "state": sqlalchemy.types.VARCHAR(64),
        "family_income_lpa": sqlalchemy.types.Float(),
    }

    perf_dtypes = {
        "student_id": sqlalchemy.types.VARCHAR(16),
        "source": sqlalchemy.types.VARCHAR(64),
        "assessment_term": sqlalchemy.types.VARCHAR(64),
        "subject": sqlalchemy.types.VARCHAR(64),
        "marks": sqlalchemy.types.Float(),
        "max_marks": sqlalchemy.types.Float(),
        "attendance_pct": sqlalchemy.types.Float(),
        "grade_or_status": sqlalchemy.types.VARCHAR(32),
    }

    life_dtypes = {
        "student_id": sqlalchemy.types.VARCHAR(16),
        "sleep_hours": sqlalchemy.types.Float(),
        "screen_time_hours": sqlalchemy.types.Float(),
        "gaming_hours": sqlalchemy.types.Float(),
        "study_hours_daily": sqlalchemy.types.Float(),
        "stress_level": sqlalchemy.types.Integer(),
        "burnout_score": sqlalchemy.types.Integer(),
        "gym_frequency_per_week": sqlalchemy.types.Integer(),
        "motivation_level": sqlalchemy.types.Integer(),
        "physical_activity_hours_sehaj": sqlalchemy.types.Float(),
        "stress_level_sehaj": sqlalchemy.types.VARCHAR(32),
        "lifestyle_risk_flag": sqlalchemy.types.VARCHAR(32),
    }

    career_dtypes = {
        "student_id": sqlalchemy.types.VARCHAR(16),
        "cgpa": sqlalchemy.types.Float(),
        "backlogs": sqlalchemy.types.Integer(),
        "internships": sqlalchemy.types.Integer(),
        "dsa_problems_solved": sqlalchemy.types.Integer(),
        "github_repos": sqlalchemy.types.Integer(),
        "coding_skills_sakhare": sqlalchemy.types.Float(),
        "communication_skills": sqlalchemy.types.Integer(),
        "aptitude_score": sqlalchemy.types.Integer(),
        "mock_interview_score": sqlalchemy.types.Integer(),
        "placement_status": sqlalchemy.types.VARCHAR(32),
        "company_type": sqlalchemy.types.VARCHAR(32),
        "work_mode": sqlalchemy.types.VARCHAR(32),
        "salary_lpa": sqlalchemy.types.Float(),
        "offer_count": sqlalchemy.types.Integer(),
        "layoffs_risk_score": sqlalchemy.types.Integer(),
    }

    return {
        "dim_student": dim_dtypes,
        "fact_performance": perf_dtypes,
        "fact_lifestyle": life_dtypes,
        "fact_career": career_dtypes,
    }


def load_to_postgres(
    dim_student: pd.DataFrame,
    fact_performance: pd.DataFrame,
    fact_lifestyle: pd.DataFrame,
    fact_career: pd.DataFrame,
    engine: Engine
):
    """
    Loads star schema tables into PostgreSQL with explicit dtypes,
    PRIMARY KEY, and FOREIGN KEY constraints.
    """
    print("\n" + "-" * 60)
    print("LOADING STAR SCHEMA INTO POSTGRESQL")
    print("-" * 60)

    dtypes = get_table_dtypes()

    # 1. Cleanly drop existing tables with CASCADE
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS fact_performance CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS fact_lifestyle CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS fact_career CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS dim_student CASCADE;"))

    # 2. Load dim_student first
    print("[POSTGRES] Loading dim_student...")
    dim_student.to_sql("dim_student", engine, if_exists="replace", index=False, dtype=dtypes["dim_student"])
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE dim_student ADD PRIMARY KEY (student_id);"))
    print("[POSTGRES] dim_student loaded and PRIMARY KEY (student_id) created.")

    # 3. Load fact_performance
    print("[POSTGRES] Loading fact_performance...")
    fact_performance.to_sql("fact_performance", engine, if_exists="replace", index=False, dtype=dtypes["fact_performance"])

    # 4. Load fact_lifestyle
    print("[POSTGRES] Loading fact_lifestyle...")
    fact_lifestyle.to_sql("fact_lifestyle", engine, if_exists="replace", index=False, dtype=dtypes["fact_lifestyle"])

    # 5. Load fact_career
    print("[POSTGRES] Loading fact_career...")
    fact_career.to_sql("fact_career", engine, if_exists="replace", index=False, dtype=dtypes["fact_career"])

    # 6. Apply Foreign Key constraints
    print("[POSTGRES] Adding Foreign Key constraints referencing dim_student(student_id)...")
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE fact_performance
            ADD CONSTRAINT fk_fact_perf_student
            FOREIGN KEY (student_id) REFERENCES dim_student(student_id) ON DELETE CASCADE;
        """))
        conn.execute(text("""
            ALTER TABLE fact_lifestyle
            ADD CONSTRAINT fk_fact_life_student
            FOREIGN KEY (student_id) REFERENCES dim_student(student_id) ON DELETE CASCADE;
        """))
        conn.execute(text("""
            ALTER TABLE fact_career
            ADD CONSTRAINT fk_fact_career_student
            FOREIGN KEY (student_id) REFERENCES dim_student(student_id) ON DELETE CASCADE;
        """))
    print("[POSTGRES] Foreign key constraints successfully enforced on all fact tables.")

    # 7. Row count validations
    print("\n[VALIDATION] Running row count verification queries on PostgreSQL tables:")
    expected_counts = {
        "dim_student": len(dim_student),
        "fact_performance": len(fact_performance),
        "fact_lifestyle": len(fact_lifestyle),
        "fact_career": len(fact_career),
    }

    with engine.connect() as conn:
        for table_name, expected in expected_counts.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            assert actual == expected, f"Row count mismatch in {table_name}: expected {expected}, got {actual}"
            print(f"  - {table_name:18}: {actual:,} rows (matches source CSV exactly)")


def load_to_sqlite(
    dim_student: pd.DataFrame,
    fact_performance: pd.DataFrame,
    fact_lifestyle: pd.DataFrame,
    fact_career: pd.DataFrame
):
    """Loads star schema tables into SQLite file (data/processed/warehouse.db) as local fallback."""
    db_path = PROCESSED_DATA_DIR / "warehouse.db"
    conn = sqlite3.connect(db_path)
    dim_student.to_sql("dim_student", conn, if_exists="replace", index=False)
    fact_performance.to_sql("fact_performance", conn, if_exists="replace", index=False)
    fact_lifestyle.to_sql("fact_lifestyle", conn, if_exists="replace", index=False)
    fact_career.to_sql("fact_career", conn, if_exists="replace", index=False)
    conn.close()
    print(f"[SQLITE FALLBACK] Star schema tables exported to: {db_path.name}")


def load_star_schema(
    wide_path: Path = PROCESSED_DATA_DIR / "student_master_wide.csv",
    save_to_db: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Builds all 4 star-schema tables and loads them into PostgreSQL (with SQLite backup)."""
    if not wide_path.exists():
        raise FileNotFoundError(f"Missing master wide dataset: {wide_path}")

    print("=" * 80)
    print("LOADING STAR SCHEMA DATA WAREHOUSE TABLES")
    print("=" * 80)

    wide_df = pd.read_csv(wide_path)

    # 1. dim_student
    dim_student = build_dim_student(wide_df)
    dim_student_path = PROCESSED_DATA_DIR / "dim_student.csv"
    dim_student.to_csv(dim_student_path, index=False)
    print(f"[CSV EXPORT] {dim_student_path.name} ({len(dim_student):,} rows x {dim_student.shape[1]} cols)")

    # 2. fact_performance
    fact_performance = build_fact_performance(wide_df)
    fact_perf_path = PROCESSED_DATA_DIR / "fact_performance.csv"
    fact_performance.to_csv(fact_perf_path, index=False)
    print(f"[CSV EXPORT] {fact_perf_path.name} ({len(fact_performance):,} rows x {fact_performance.shape[1]} cols)")

    # 3. fact_lifestyle
    fact_lifestyle = build_fact_lifestyle(wide_df)
    fact_life_path = PROCESSED_DATA_DIR / "fact_lifestyle.csv"
    fact_lifestyle.to_csv(fact_life_path, index=False)
    print(f"[CSV EXPORT] {fact_life_path.name} ({len(fact_lifestyle):,} rows x {fact_lifestyle.shape[1]} cols)")

    # 4. fact_career
    fact_career = build_fact_career(wide_df)
    fact_career_path = PROCESSED_DATA_DIR / "fact_career.csv"
    fact_career.to_csv(fact_career_path, index=False)
    print(f"[CSV EXPORT] {fact_career_path.name} ({len(fact_career):,} rows x {fact_career.shape[1]} cols)")

    if save_to_db:
        # Always maintain SQLite warehouse file as offline/demo fallback
        load_to_sqlite(dim_student, fact_performance, fact_lifestyle, fact_career)

        # Connect to active database engine
        engine, engine_type = create_warehouse_engine()
        if engine_type == "postgres":
            load_to_postgres(dim_student, fact_performance, fact_lifestyle, fact_career, engine)
        else:
            print("[INFO] DB_ENGINE is set to sqlite (or postgres unavailable); SQLite warehouse is active.")

    print("=" * 80 + "\n")
    return dim_student, fact_performance, fact_lifestyle, fact_career


def main():
    load_star_schema()


if __name__ == "__main__":
    main()
