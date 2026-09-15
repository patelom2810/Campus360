"""
Unit & Integration Tests for KDAC-3 ETL Pipeline
Tests raw dataset ingestion, cleaning rules, student_id stitching,
relational tables, and model-ready training datasets.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = BASE_DIR / "data" / "raw"


class TestETLPipeline(unittest.TestCase):

    def test_raw_files_exist(self):
        expected_files = [
            "1_student_records.csv",
            "2_exam_marks.csv",
            "3_attendance.csv",
            "4_lifestyle.csv",
            "5_skills.csv",
            "6_career_preferences.csv",
        ]
        for f in expected_files:
            self.assertTrue((RAW_DIR / f).exists(), f"Raw file missing: {f}")

    def test_stitched_master_integrity(self):
        stitched_path = PROCESSED_DIR / "student_master_stitched.csv"
        self.assertTrue(stitched_path.exists(), "student_master_stitched.csv missing")
        df = pd.read_csv(stitched_path)
        self.assertEqual(len(df), 10000, f"Expected 10,000 rows, got {len(df)}")
        self.assertEqual(df["student_id"].nunique(), 10000, "student_id must be strictly unique")
        self.assertEqual(df["student_id"].iloc[0], "S100000")
        self.assertEqual(df["student_id"].iloc[-1], "S109999")

    def test_relational_warehouse_tables(self):
        tables = [
            "cleaned_students.csv",
            "cleaned_academic_records.csv",
            "cleaned_exam_marks.csv",
            "cleaned_attendance.csv",
            "cleaned_lifestyle.csv",
            "cleaned_skills.csv",
            "cleaned_career_preferences.csv",
        ]
        master_ids = None
        for tbl in tables:
            tbl_path = PROCESSED_DIR / tbl
            self.assertTrue(tbl_path.exists(), f"Warehouse table missing: {tbl}")
            df = pd.read_csv(tbl_path)
            self.assertEqual(len(df), 10000, f"Table {tbl} row count mismatch: {len(df)}")
            if tbl == "cleaned_students.csv":
                master_ids = set(df["student_id"])
            else:
                self.assertEqual(set(df["student_id"]), master_ids, f"Referential mismatch in {tbl}")

    def test_model_training_datasets(self):
        at_risk_path = PROCESSED_DIR / "at_risk_dataset.csv"
        perf_path = PROCESSED_DIR / "student_performance_dataset.csv"

        self.assertTrue(at_risk_path.exists(), "at_risk_dataset.csv missing in data/processed")
        self.assertTrue(perf_path.exists(), "student_performance_dataset.csv missing in data/processed")

        df_risk = pd.read_csv(at_risk_path)
        df_perf = pd.read_csv(perf_path)

        self.assertEqual(len(df_risk), 10000)
        self.assertEqual(len(df_perf), 10000)

        self.assertIn("at_risk_flag", df_risk.columns)
        self.assertIn("next_semester_marks", df_perf.columns)
        self.assertTrue(df_risk["at_risk_flag"].isin([0, 1]).all())


if __name__ == "__main__":
    unittest.main()
