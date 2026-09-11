"""
Unit tests for fix_and_prepare.py ETL remediation and model preparation.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESSED_DIR = BASE_DIR / "data" / "processed"
from src.etl.fix_and_prepare import MODEL_1_FEATURES, MODEL_2_FEATURES, MODEL_1_TARGET, MODEL_2_TARGET


class TestFixAndPrepare(unittest.TestCase):

    def setUp(self):
        self.m1_train_path = PROCESSED_DIR / "model1_performance_train.csv"
        self.m1_test_path = PROCESSED_DIR / "model1_performance_test.csv"
        self.m2_train_path = PROCESSED_DIR / "model2_atrisk_train.csv"
        self.m2_test_path = PROCESSED_DIR / "model2_atrisk_test.csv"
        self.wide_path = PROCESSED_DIR / "student_master_wide.csv"
        self.pii_log = PROCESSED_DIR / "pii_removal_log.md"
        self.notes = PROCESSED_DIR / "label_engineering_notes.md"

    def test_artifacts_exist(self):
        for path in [
            self.m1_train_path,
            self.m1_test_path,
            self.m2_train_path,
            self.m2_test_path,
            self.wide_path,
            self.pii_log,
            self.notes,
        ]:
            self.assertTrue(path.exists(), f"Missing artifact: {path.name}")

    def test_pii_completely_removed(self):
        df_wide = pd.read_csv(self.wide_path)
        pii_cols = [c for c in df_wide.columns if any(term in c.lower() for term in ["name", "email"])]
        self.assertEqual(len(pii_cols), 0, f"Found PII columns in master wide: {pii_cols}")

    def test_kundan_final_grade_casing(self):
        df_wide = pd.read_csv(self.wide_path)
        grades = set(df_wide["kundan_final_grade"].dropna().unique())
        self.assertTrue(grades.issubset({"A", "B", "C", "D", "E", "F"}), f"Invalid grades: {grades}")

    def test_model1_dataset_integrity(self):
        train = pd.read_csv(self.m1_train_path)
        test = pd.read_csv(self.m1_test_path)

        self.assertEqual(len(train), 20000)
        self.assertEqual(len(test), 5000)
        self.assertEqual(train.isnull().sum().sum(), 0)
        self.assertEqual(test.isnull().sum().sum(), 0)

        expected_cols = set(MODEL_1_FEATURES + [MODEL_1_TARGET])
        self.assertEqual(set(train.columns), expected_cols)
        self.assertEqual(set(test.columns), expected_cols)

    def test_model2_dataset_integrity_and_leakage(self):
        train = pd.read_csv(self.m2_train_path)
        test = pd.read_csv(self.m2_test_path)

        self.assertEqual(len(train), 20000)
        self.assertEqual(len(test), 5000)
        self.assertEqual(train.isnull().sum().sum(), 0)
        self.assertEqual(test.isnull().sum().sum(), 0)

        expected_cols = set(MODEL_2_FEATURES + [MODEL_2_TARGET])
        self.assertEqual(set(train.columns), expected_cols)
        self.assertEqual(set(test.columns), expected_cols)

        # Leakage check
        forbidden = {"anchor_backlog_history", "anchor_attendance_percentage", "anchor_cgpa"}
        self.assertTrue(forbidden.isdisjoint(set(train.columns) - {MODEL_2_TARGET}))

        # Stratification check
        train_rate = train[MODEL_2_TARGET].mean()
        test_rate = test[MODEL_2_TARGET].mean()
        self.assertAlmostEqual(train_rate, test_rate, delta=0.01)
        self.assertTrue(0.20 <= train_rate <= 0.35, f"Rate {train_rate} out of target bounds")


if __name__ == "__main__":
    unittest.main()
