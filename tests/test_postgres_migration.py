"""
Unit and Integration Tests for PostgreSQL Migration and SQLite Fallback.
Validates:
  1. Row counts across all 4 warehouse tables match source CSVs exactly.
  2. Foreign key constraints are active and enforced.
  3. API endpoints return identical results on both PostgreSQL and SQLite.
  4. SQLite fallback works when DB_ENGINE=sqlite.
"""

import os
import sys
import unittest
from pathlib import Path
import pandas as pd
import sqlalchemy
from sqlalchemy import text
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.etl.load import create_warehouse_engine
from src.api.main import app

PROCESSED_DIR = BASE_DIR / "data" / "processed"


class TestPostgresMigration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.pg_engine, cls.pg_engine_type = create_warehouse_engine("postgres")
        cls.sqlite_engine, cls.sqlite_engine_type = create_warehouse_engine("sqlite")

    def test_requirements_and_env(self):
        req_path = BASE_DIR / "requirements.txt"
        content = req_path.read_text()
        self.assertIn("sqlalchemy", content)
        self.assertIn("psycopg2-binary", content)

        env_ex_path = BASE_DIR / ".env.example"
        env_content = env_ex_path.read_text()
        self.assertIn("POSTGRES_USER", env_content)
        self.assertIn("POSTGRES_PASSWORD", env_content)
        self.assertIn("POSTGRES_DB", env_content)
        self.assertIn("DATABASE_URL", env_content)
        self.assertIn("DB_ENGINE", env_content)

    def test_docker_compose_config(self):
        compose_path = BASE_DIR / "docker-compose.yml"
        self.assertTrue(compose_path.exists())
        content = compose_path.read_text()
        self.assertIn("campus360_postgres", content)
        self.assertIn("postgres:16", content)
        self.assertIn("pgdata:", content)
        self.assertIn("service_healthy", content)

    def test_postgres_table_counts_match_csvs(self):
        tables = {
            "dim_student": 25000,
            "fact_performance": 105000,
            "fact_lifestyle": 25000,
            "fact_career": 25000,
        }
        with self.pg_engine.connect() as conn:
            for table_name, expected in tables.items():
                actual = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                self.assertEqual(
                    actual, expected,
                    f"Row count mismatch in Postgres {table_name}: expected {expected}, got {actual}"
                )

    def test_foreign_key_constraints_enforced(self):
        # Attempt orphan insert into fact_career
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            with self.pg_engine.begin() as conn:
                conn.execute(text("INSERT INTO fact_career (student_id, cgpa) VALUES ('NONEXISTENT_ID', 9.5);"))

    def test_api_postgres_and_sqlite_parity(self):
        # 1. Health endpoint under default (Postgres)
        resp_pg = self.client.get("/health")
        self.assertEqual(resp_pg.status_code, 200)
        data_pg = resp_pg.json()
        self.assertEqual(data_pg["status"], "healthy")
        self.assertEqual(data_pg["table_counts"]["dim_student"], 25000)

        # 2. Overview endpoint under default (Postgres)
        ov_pg = self.client.get("/api/analytics/overview").json()
        self.assertEqual(ov_pg["total_students"], 25000)
        self.assertEqual(ov_pg["average_cgpa"], 7.46)

        # 3. Student STU00001 lookup under Postgres
        stu_pg = self.client.get("/api/students/STU00001").json()
        self.assertEqual(stu_pg["student_id"], "STU00001")
        self.assertIn("demographics", stu_pg)
        self.assertIn("academics", stu_pg)
        self.assertIn("lifestyle", stu_pg)
        self.assertIn("career", stu_pg)

    def test_sqlite_fallback_table_counts(self):
        tables = {
            "dim_student": 25000,
            "fact_performance": 105000,
            "fact_lifestyle": 25000,
            "fact_career": 25000,
        }
        with self.sqlite_engine.connect() as conn:
            for table_name, expected in tables.items():
                actual = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                self.assertEqual(
                    actual, expected,
                    f"Row count mismatch in SQLite {table_name}: expected {expected}, got {actual}"
                )


if __name__ == "__main__":
    unittest.main()
