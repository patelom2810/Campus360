"""
Unit tests for Campus360 ML Models and Inference Pipeline.
Validates:
  1. Serialized model artifacts exist and can be unpickled.
  2. Model 1 (Random Forest Regressor) produces valid predictions in range [0, 100].
  3. Model 2 (At-Risk Classifier) produces calibrated probability scores in range [0, 1].
  4. Batch inference helper (predict_batch) executes cleanly without target leakage.
"""

import sys
import unittest
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import MODEL_1_PATH, MODEL_2_PATH, PROCESSED_DATA_DIR
from genai.generate_insights import predict_batch, get_ml_predictions


class TestMLModels(unittest.TestCase):

    def setUp(self):
        self.assertTrue(MODEL_1_PATH.exists(), f"Model 1 artifact missing at {MODEL_1_PATH}")
        self.assertTrue(MODEL_2_PATH.exists(), f"Model 2 artifact missing at {MODEL_2_PATH}")
        self.m1 = joblib.load(MODEL_1_PATH)
        self.m2 = joblib.load(MODEL_2_PATH)

    def test_model_artifacts_and_features(self):
        m1_features = list(getattr(self.m1, "feature_names_in_", []))
        m2_features = list(getattr(self.m2, "feature_names_in_", []))

        self.assertGreater(len(m1_features), 0, "Model 1 has no feature_names_in_")
        self.assertGreater(len(m2_features), 0, "Model 2 has no feature_names_in_")

        # Zero Target Leakage Checks
        leakage_forbidden = {"next_semester_marks", "performance_band"}
        self.assertTrue(leakage_forbidden.isdisjoint(set(m1_features)), "Model 1 contains leaked target columns!")
        self.assertTrue(leakage_forbidden.isdisjoint(set(m2_features)), "Model 2 contains leaked target columns!")

    def test_single_student_prediction(self):
        preds = get_ml_predictions("S100000")
        self.assertIn("predicted_marks", preds)
        self.assertIn("predicted_risk_prob", preds)
        self.assertIn("risk_classification", preds)
        self.assertTrue(0.0 <= preds["predicted_marks"] <= 100.0)
        self.assertTrue(0.0 <= preds["predicted_risk_prob"] <= 1.0)
        self.assertIn(preds["risk_classification"], ["At-Risk (High Priority)", "On-Track"])

    def test_batch_prediction_pipeline(self):
        stitched_csv = PROCESSED_DATA_DIR / "student_master_stitched.csv"
        self.assertTrue(stitched_csv.exists(), "Master stitched dataset missing")
        sample_df = pd.read_csv(stitched_csv).head(20)

        batch_results = predict_batch(sample_df)
        self.assertEqual(len(batch_results), 20)
        self.assertIn("predicted_next_sem_marks", batch_results.columns)
        self.assertIn("predicted_risk_prob", batch_results.columns)
        self.assertIn("risk_classification", batch_results.columns)

        # Check output value ranges
        self.assertTrue((batch_results["predicted_next_sem_marks"] >= 0).all())
        self.assertTrue((batch_results["predicted_next_sem_marks"] <= 100).all())
        self.assertTrue((batch_results["predicted_risk_prob"] >= 0).all())
        self.assertTrue((batch_results["predicted_risk_prob"] <= 1).all())


if __name__ == "__main__":
    unittest.main()
