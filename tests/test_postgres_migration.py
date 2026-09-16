"""
Unit and Integration Tests for Warehouse Architecture and SQLite/PostgreSQL Fallback.
Validates:
  1. Requirements and Docker configuration files exist.
  2. Database engine connectivity and query execution.
  3. Row counts across all 7 warehouse tables match 10,000 students.
  4. All 4 analytical SQL views exist and execute cleanly.
  5. Referential integrity and foreign key constraints.
"""

import sys
import unittest
from pathlib import Path
import sqlalchemy
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import get_db_engine, WAREHOUSE_DB_PATH


class TestWarehouseAndMigration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = get_db_engine()

    def test_requirements_and_env(self):
        req_path = BASE_DIR / "requirements.txt"
        self.assertTrue(req_path.exists())
        content = req_path.read_text()
        self.assertIn("sqlalchemy", content)

        env_ex_path = BASE_DIR / ".env.example"
        self.assertTrue(env_ex_path.exists())

    def test_docker_compose_config(self):
        compose_path = BASE_DIR / "docker-compose.yml"
        self.assertTrue(compose_path.exists())
        content = compose_path.read_text()
        self.assertIn("campus360_postgres", content)
        self.assertIn("postgres:16", content)

    def test_warehouse_table_counts(self):
        tables = [
            "students",
            "academic_records",
            "exam_marks",
            "attendance",
            "lifestyle",
            "skills",
            "career_preferences",
        ]
        with self.engine.connect() as conn:
            for table_name in tables:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                self.assertEqual(
                    count, 10000,
                    f"Row count mismatch in table {table_name}: expected 10,000, got {count}"
                )

    def test_analytical_views_queryable(self):
        views = [
            "student_360_view",
            "performance_features_view",
            "at_risk_features_view",
            "career_readiness_view",
        ]
        with self.engine.connect() as conn:
            for view_name in views:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()
                self.assertEqual(
                    count, 10000,
                    f"Analytical view {view_name} did not return 10,000 records (got {count})"
                )

    def test_referential_integrity(self):
        child_tables = [
            "academic_records",
            "exam_marks",
            "attendance",
            "lifestyle",
            "skills",
            "career_preferences",
        ]
        with self.engine.connect() as conn:
            for child in child_tables:
                orphan_query = text(f"""
                    SELECT COUNT(*) 
                    FROM {child} c 
                    LEFT JOIN students s ON c.student_id = s.student_id 
                    WHERE s.student_id IS NULL
                """)
                orphans = conn.execute(orphan_query).scalar()
                self.assertEqual(orphans, 0, f"Found {orphans} orphaned records in child table {child}")


if __name__ == "__main__":
    unittest.main()
