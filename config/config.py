"""
Configuration Module for KDAC-3 Data Engineering Pipeline.
Loads environment variables and sets up project paths and database connections.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Base Paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"

# Load .env file
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Database Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
# Default to 5433 since docker-compose maps host 5433 -> container 5432
POSTGRES_PORT = int(os.getenv("POSTGRES_HOST_PORT", os.getenv("POSTGRES_PORT", "5433")))
POSTGRES_DB = os.getenv("POSTGRES_DB", "campus360_warehouse")
POSTGRES_USER = os.getenv("POSTGRES_USER", "campus360")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Raw files mapping and their respective student identifier columns
RAW_DATASET_MAPPING = {
    "1_student_records.csv": "student_id",
    "2_exam_marks.csv": "StudentID",
    "3_attendance.csv": "roll_no",
    "4_lifestyle.csv": "student_id",
    "5_skills.csv": "STUDENT_ID",
    "6_career_preferences.csv": "roll_number",
}

def get_db_engine():
    """Returns an SQLAlchemy engine connected to PostgreSQL, testing connection."""
    # Attempt primary connection
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect():
            pass
        return engine
    except Exception as primary_err:
        # Fallback to alternate port (5432 <-> 5433)
        alt_port = 5432 if POSTGRES_PORT == 5433 else 5433
        alt_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{alt_port}/{POSTGRES_DB}"
        try:
            alt_engine = create_engine(alt_url, pool_pre_ping=True)
            with alt_engine.connect():
                pass
            return alt_engine
        except Exception:
            raise primary_err
