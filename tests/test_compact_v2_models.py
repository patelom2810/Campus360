"""
tests/test_compact_v2_models.py
Automated validation tests for Compact v2 Models:
  - Model 1: 10-feature GradientBoostingRegressor (target: anchor_cgpa)
  - Model 2: 10-feature LogisticRegression (target: at_risk_flag)
  - Edge cases: normal, high-performing, struggling, sparse, extreme inputs
  - Model explainability signals and probability bounds
"""

import os
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
import src.api.main as main_mod
import src.api.assessment_engine as assess_mod
from src.api.assessment_engine import run_full_assessment
from src.api.main import get_model1, get_model2


class TestCompactV2Models(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_version = os.environ.get("MODEL_VERSION", "v1")
        os.environ["MODEL_VERSION"] = "v2"
        main_mod._MODEL1 = None
        main_mod._MODEL2 = None
        assess_mod._MODEL1_CACHE = None
        assess_mod._MODEL2_CACHE = None
        cls.m1, cls.meta1, cls.medians1 = get_model1()
        cls.m2, cls.meta2 = get_model2()

    @classmethod
    def tearDownClass(cls):
        os.environ["MODEL_VERSION"] = cls.orig_version
        main_mod._MODEL1 = None
        main_mod._MODEL2 = None
        assess_mod._MODEL1_CACHE = None
        assess_mod._MODEL2_CACHE = None

    def test_v2_models_loaded_correctly(self):
        """Verify v2 compact models are loaded with exactly 10 features each."""
        self.assertEqual(len(self.meta1["features"]), 10)
        self.assertEqual(len(self.meta2["features"]), 10)
        self.assertEqual(self.meta1["target"], "anchor_cgpa")
        self.assertEqual(self.meta2["target"], "at_risk_flag")

    def test_v2_model2_zero_leakage(self):
        """Verify Model 2 excludes all target-defining columns."""
        leaked = {"anchor_backlog_history", "anchor_attendance_percentage", "anchor_cgpa"}
        overlap = set(self.meta2["features"]).intersection(leaked)
        self.assertEqual(len(overlap), 0, f"Leakage found in v2 Model 2: {overlap}")

    def test_normal_student(self):
        payload = {
            "anchor_attendance_percentage": 82.0,
            "anchor_study_hours_daily": 4.5,
            "anchor_sleep_hours": 7.0,
            "anchor_stress_level": 50.0,
            "anchor_burnout_score": 40.0,
            "anchor_dsa_problems_solved": 150,
            "anchor_internships_completed": 1,
            "anchor_communication_skills": 72.0,
            "anchor_aptitude_score": 68.0,
            "anchor_screen_time": 5.0,
            "anchor_gym_frequency": 3,
            "anchor_self_learning_hours": 2.0,
            "anchor_gaming_hours": 1.5,
            "anchor_development_projects_count": 2,
            "branch": "Computer Science",
            "college_tier": 1,
        }
        res = run_full_assessment(payload)
        self.assertTrue(5.0 <= res["predicted_cgpa"] <= 10.0)
        self.assertTrue(0.0 <= res["at_risk_probability"] <= 1.0)
        self.assertIn(res["at_risk_label"], ["Safe", "At-Risk"])
        self.assertIsNotNone(res["genai_payloads"]["atrisk_payload"]["top_factor"])

    def test_high_performing_student(self):
        payload = {
            "anchor_attendance_percentage": 96.0,
            "anchor_study_hours_daily": 8.0,
            "anchor_sleep_hours": 8.0,
            "anchor_stress_level": 20.0,
            "anchor_burnout_score": 15.0,
            "anchor_dsa_problems_solved": 450,
            "anchor_internships_completed": 3,
            "anchor_communication_skills": 90.0,
            "anchor_aptitude_score": 92.0,
            "anchor_screen_time": 3.0,
            "anchor_gym_frequency": 5,
            "anchor_self_learning_hours": 4.0,
            "anchor_gaming_hours": 0.5,
            "anchor_development_projects_count": 5,
            "branch": "Computer Science",
            "college_tier": 1,
        }
        res = run_full_assessment(payload)
        self.assertGreaterEqual(res["predicted_cgpa"], 7.0)
        self.assertEqual(res["at_risk_label"], "Safe")
        self.assertTrue(res["career_readiness"]["career_readiness_score"] > 0)

    def test_struggling_student(self):
        payload = {
            "anchor_attendance_percentage": 42.0,
            "anchor_study_hours_daily": 1.0,
            "anchor_sleep_hours": 4.0,
            "anchor_stress_level": 92.0,
            "anchor_burnout_score": 88.0,
            "anchor_dsa_problems_solved": 10,
            "anchor_internships_completed": 0,
            "anchor_communication_skills": 40.0,
            "anchor_aptitude_score": 38.0,
            "anchor_screen_time": 9.0,
            "anchor_gym_frequency": 0,
            "anchor_self_learning_hours": 0.2,
            "anchor_gaming_hours": 5.0,
            "anchor_development_projects_count": 0,
            "branch": "Information Technology",
            "college_tier": 3,
        }
        res = run_full_assessment(payload)
        self.assertTrue(0.0 <= res["predicted_cgpa"] <= 10.0)
        self.assertEqual(res["at_risk_label"], "At-Risk")
        self.assertGreaterEqual(res["at_risk_probability"], 0.50)

    def test_sparse_and_extreme_inputs(self):
        # Sparse
        res_sparse = run_full_assessment({"anchor_study_hours_daily": 3.0})
        self.assertTrue(0.0 <= res_sparse["predicted_cgpa"] <= 10.0)
        self.assertTrue(0.0 <= res_sparse["at_risk_probability"] <= 1.0)
        
        # Extreme
        extreme = {
            "anchor_attendance_percentage": 100.0,
            "anchor_study_hours_daily": 16.0,
            "anchor_sleep_hours": 0.0,
            "anchor_stress_level": 100.0,
            "anchor_burnout_score": 100.0,
            "anchor_dsa_problems_solved": 2000,
            "anchor_internships_completed": 10,
            "anchor_screen_time": 16.0,
        }
        res_extreme = run_full_assessment(extreme)
        self.assertTrue(0.0 <= res_extreme["predicted_cgpa"] <= 10.0)
        self.assertTrue(0.0 <= res_extreme["at_risk_probability"] <= 1.0)


if __name__ == "__main__":
    unittest.main()
