"""
Campus360 — Central Configuration & Path Registry
Single source of truth for all database connections, directory paths,
model artifacts, and API configurations.
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ── Base Directory Hierarchy ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Environment & API Keys ─────────────────────────────────────────────────────
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", os.getenv("groq_api", ""))
GENAI_LOG_PATH = LOGS_DIR / "genai_prompts.log"

# ── Model Artifact Paths ───────────────────────────────────────────────────────
MODEL_1_PATH = MODELS_DIR / "next_semester_marks_model.pkl"
MODEL_2_PATH = MODELS_DIR / "at_risk_classifier_model.pkl"

MODEL_1_TRAIN_CSV = PROCESSED_DATA_DIR / "model1_performance_train.csv"
MODEL_1_TEST_CSV  = PROCESSED_DATA_DIR / "model1_performance_test.csv"
MODEL_2_TRAIN_CSV = PROCESSED_DATA_DIR / "model2_atrisk_train.csv"
MODEL_2_TEST_CSV  = PROCESSED_DATA_DIR / "model2_atrisk_test.csv"

# ── Database Configuration (SQLite Warehouse) ─────────────────────────────────
# Selected Option A: Embedded SQLite warehouse for zero external dependencies,
# high performance, complete reproducibility, and seamless portability.
WAREHOUSE_DB_PATH = PROCESSED_DATA_DIR / "warehouse.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{WAREHOUSE_DB_PATH}")

# ── Raw Dataset Mapping ───────────────────────────────────────────────────────
RAW_DATASET_MAPPING = {
    "1_student_records.csv": "student_id",
    "2_exam_marks.csv": "StudentID",
    "3_attendance.csv": "roll_no",
    "4_lifestyle.csv": "student_id",
    "5_skills.csv": "STUDENT_ID",
    "6_career_preferences.csv": "roll_number",
}


def get_db_engine():
    """Returns an SQLAlchemy engine connected to the SQLite warehouse."""
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    )
    return engine


def get_db_connection() -> sqlite3.Connection:
    """Returns a direct sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(str(WAREHOUSE_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
