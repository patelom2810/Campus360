"""
tests/test_dashboard_api.py
Automated test suite verifying the Campus360 analytics endpoints,
server-side normalization, at-risk classification, and performance forecasting.
"""

import unittest
from fastapi.testclient import TestClient
from src.api.main import app


class TestDashboardAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_healthcheck(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("dim_student", data["table_counts"])
        self.assertTrue(data["models_ready"]["model1_performance_predictor"])
        self.assertTrue(data["models_ready"]["model2_atrisk_classifier"])

    def test_analytics_overview(self):
        res = self.client.get("/api/analytics/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_students"], 25000)
        self.assertGreater(data["average_cgpa"], 7.0)
        self.assertLess(data["average_cgpa"], 8.5)
        self.assertGreater(data["placement_rate_pct"], 50.0)
        # Verify calibrated at-risk rate matches stratified 31.9%
        self.assertAlmostEqual(data["at_risk_pct"], 31.9, delta=0.5)

        # Verify CGPA histogram bins
        bins = data["cgpa_distribution"]
        self.assertEqual(len(bins), 5)
        total_binned = sum(b["count"] for b in bins)
        self.assertEqual(total_binned, 25000)

    def test_at_risk_students_quicklist(self):
        res = self.client.get("/api/analytics/at-risk-students?limit=6")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        students = data["students"]
        self.assertEqual(len(students), 6)
        for s in students:
            self.assertTrue(s["student_id"].startswith("STU"))
            self.assertGreaterEqual(s["predicted_risk_probability"], 0.50)
            self.assertEqual(s["risk_label"], "At-Risk")
            self.assertTrue(len(s["top_contributing_factor"]) > 0)

    def test_subject_performance_normalization(self):
        res = self.client.get("/api/analytics/subjects")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Check overall subjects
        overall = {item["subject"]: item["avg_normalized_pct"] for item in data["overall_subjects"]}
        self.assertIn("Degree CGPA", overall)
        self.assertIn("Mathematics", overall)
        self.assertIn("Science", overall)

        # Critical validation: Degree CGPA must be normalized to ~74-75% on 0-100 scale, NOT 7.46!
        self.assertGreater(overall["Degree CGPA"], 50.0, "Degree CGPA must be on 0-100 scale, not 0-10 raw scale")
        self.assertLess(overall["Degree CGPA"], 95.0)

        # Heatmap matrix
        self.assertTrue(len(data["heatmap_matrix"]) >= 6)
        self.assertTrue(len(data["branches"]) >= 6)

        # Lowest-performing per branch table
        lowest = data["lowest_performing_per_branch"]
        self.assertEqual(len(lowest), len(data["branches"]))
        for entry in lowest:
            self.assertIn(entry["gap_severity"], ["High Gap", "Moderate Gap", "Low Gap"])

    def test_atrisk_metadata_and_disclosure(self):
        res = self.client.get("/api/models/atrisk-metadata")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Population split close to 32% / 68%
        split = data["population_split"]
        self.assertAlmostEqual(split["at_risk_pct"], 31.9, delta=0.5)
        self.assertAlmostEqual(split["safe_pct"], 68.1, delta=0.5)

        # Top 5 features
        top_5 = data["top_5_features"]
        self.assertEqual(len(top_5), 5)
        for f in top_5:
            self.assertIn("feature", f)
            self.assertIn("label", f)
            self.assertGreater(f["importance"], 0.0)

        # Honest disclosure text
        self.assertIn("recall 0.45", data["disclosure_text"])
        self.assertIn("lifestyle and behavioral data alone", data["disclosure_text"])

    def test_atrisk_table_pagination_and_search(self):
        res = self.client.get("/api/analytics/atrisk-table?limit=10&offset=0")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["students"]), 10)
        self.assertEqual(data["total"], 25000)

        # Search test
        search_res = self.client.get("/api/analytics/atrisk-table?search=STU15140")
        self.assertEqual(search_res.status_code, 200)
        search_data = search_res.json()
        self.assertGreaterEqual(len(search_data["students"]), 1)
        self.assertEqual(search_data["students"][0]["student_id"], "STU15140")

    def test_performance_prediction_sensitivity(self):
        # Low effort inputs
        low_res = self.client.post("/api/models/predict-performance", json={
            "attendance_percentage": 55.0,
            "study_hours_daily": 1.0,
            "dsa_problems_solved": 15,
            "internships_completed": 0,
            "sleep_hours": 4.5,
            "communication_skills": 40.0
        })
        self.assertEqual(low_res.status_code, 200)
        low_cgpa = low_res.json()["predicted_cgpa"]

        # High effort inputs
        high_res = self.client.post("/api/models/predict-performance", json={
            "attendance_percentage": 95.0,
            "study_hours_daily": 8.0,
            "dsa_problems_solved": 400,
            "internships_completed": 3,
            "sleep_hours": 7.5,
            "communication_skills": 90.0
        })
        self.assertEqual(high_res.status_code, 200)
        high_cgpa = high_res.json()["predicted_cgpa"]

        # Sliders must meaningfully change the outcome
        self.assertGreater(high_cgpa, low_cgpa)
        self.assertAlmostEqual(high_res.json()["model_r2"], 0.2096, places=3)
        self.assertIn("R² is 0.21", high_res.json()["confidence_note"])

    def test_student_360_lookup(self):
        res = self.client.get("/api/students/STU00001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_id"], "STU00001")
        self.assertIn("demographics", data)
        self.assertIn("academics", data)
        self.assertIn("lifestyle", data)
        self.assertIn("career", data)

        # Check normalized percentage in academics
        for a in data["academics"]:
            if a["marks"] is not None and a["max_marks"]:
                self.assertIsNotNone(a["normalized_pct"])

        # Non-existent student returns 404
        not_found = self.client.get("/api/students/STU99999999")
        self.assertEqual(not_found.status_code, 404)


if __name__ == "__main__":
    unittest.main()
