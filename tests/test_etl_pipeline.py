"""
Unit & Integration Tests for ETL Pipeline
Tests data ingestion, cleaning rules, attribute-based stitching, and star schema tables.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESSED_DIR = BASE_DIR / "data" / "processed"
INTERIM_DIR = BASE_DIR / "data" / "interim"
RAW_DIR = BASE_DIR / "data" / "raw"


class TestETLPipeline(unittest.TestCase):

    def test_raw_files_exist(self):
        expected_files = [
            "suvidya_student_performance.csv",
            "kundan_student_performance.csv",
            "sehaj_student_lifestyle.csv",
            "navinpatidar_indian_placement.csv",
            "sakharebharat_indian_placement_2025.csv",
            "shambhuraje_placement_career_2026.csv"
        ]
        for f in expected_files:
            self.assertTrue((RAW_DIR / f).exists(), f"Raw file missing: {f}")

    def test_interim_files_clean(self):
        for clean_file in INTERIM_DIR.glob("*_clean.csv"):
            df = pd.read_csv(clean_file)
            self.assertGreater(len(df), 0, f"Cleaned file is empty: {clean_file.name}")
            for c in df.columns:
                self.assertEqual(c, c.lower(), f"Column not lowercase snake_case: {c} in {clean_file.name}")

    def test_wide_master_integrity(self):
        wide_path = PROCESSED_DIR / "student_master_wide.csv"
        self.assertTrue(wide_path.exists())
        df = pd.read_csv(wide_path)
        self.assertEqual(len(df), 25000, f"Expected 25,000 rows, got {len(df)}")
        self.assertEqual(df["student_id"].nunique(), 25000, "student_id must be strictly unique")
        self.assertEqual(df["student_id"].iloc[0], "STU00001")
        self.assertEqual(df["student_id"].iloc[-1], "STU25000")

    def test_star_schema_relationships(self):
        dim_student = pd.read_csv(PROCESSED_DIR / "dim_student.csv")
        fact_career = pd.read_csv(PROCESSED_DIR / "fact_career.csv")
        fact_lifestyle = pd.read_csv(PROCESSED_DIR / "fact_lifestyle.csv")
        fact_perf = pd.read_csv(PROCESSED_DIR / "fact_performance.csv")

        self.assertEqual(len(dim_student), 25000)
        self.assertEqual(len(fact_career), 25000)
        self.assertEqual(len(fact_lifestyle), 25000)
        self.assertEqual(len(fact_perf), 105000)

        # Foreign key integrity
        student_id_set = set(dim_student["student_id"])
        self.assertEqual(set(fact_career["student_id"]), student_id_set)
        self.assertEqual(set(fact_lifestyle["student_id"]), student_id_set)
        self.assertTrue(set(fact_perf["student_id"]).issubset(student_id_set))

    def test_statistical_realism(self):
        wide_df = pd.read_csv(PROCESSED_DIR / "student_master_wide.csv")
        sub = wide_df[["anchor_cgpa", "sakhare_cgpa"]].dropna()
        corr = sub["anchor_cgpa"].corr(sub["sakhare_cgpa"])
        self.assertGreater(corr, 0.70, f"Correlation between Anchor and Sakhare CGPA is too low: {corr}")


if __name__ == "__main__":
    unittest.main()
