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

    def test_career_guidance_endpoint(self):
        # 1. Successful lookup and composite readiness score
        res = self.client.get("/api/students/STU00001/career-guidance")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_id"], "STU00001")
        self.assertEqual(data["branch"], "Computer Science")
        self.assertEqual(data["college_tier"], 2)

        # Career Readiness Score in range [0, 100]
        score = data["career_readiness_score"]
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

        # 2. Peer Benchmark uses branch + tier subgroup
        peer = data["peer_benchmark"]
        self.assertIn("peer_avg_readiness", peer)
        self.assertEqual(peer["peer_group"], "Computer Science · Tier 2")
        self.assertGreater(peer["peer_count"], 100)

        # 3. Skill gap breakdown: 6 components sorted ascending by percentile
        gaps = data["skill_gap_breakdown"]
        self.assertEqual(len(gaps), 6)
        percentiles = [g["percentile_in_branch"] for g in gaps]
        self.assertEqual(percentiles, sorted(percentiles))

        # 4. Suggested Focus Area is based on lowest-percentile component
        focus = data["suggested_focus_area"]
        self.assertEqual(focus["component"], gaps[0]["component"])
        self.assertTrue(len(focus["suggestion"]) > 10)

        # 5. Placement outcome reference is descriptive and includes disclosure
        pref = data["placement_outcome_reference"]
        self.assertIn("placement_rate_pct", pref)
        self.assertIn("readiness_band", pref)
        self.assertIn("peer reference", data["disclosure"].lower())
        self.assertIn("not a personal prediction", data["disclosure"].lower())

        # 6. Suggestions vary across students with different weaknesses
        res2 = self.client.get("/api/students/STU15140/career-guidance")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        # STU15140 (Mechanical) has DSA lowest, unlike STU00001 (Projects lowest)
        self.assertNotEqual(
            data["suggested_focus_area"]["component"],
            data2["suggested_focus_area"]["component"]
        )

        # 7. Non-existent student returns 404
        not_found = self.client.get("/api/students/STU99999999/career-guidance")
        self.assertEqual(not_found.status_code, 404)

    def test_career_guidance_small_peer_group(self):
        """
        Verify that students in tail score percentiles whose initial ±10 readiness band has
        fewer than 30 peer students trigger progressive band widening (±15 or ±20) to maintain
        a statistically reliable peer outcome reference (>= 30 peers).
        """
        # STU24598: Score 86.7 (CS Tier 2). Peer count at ±10 is 4 (<30), ±15 is 12 (<30), ±20 is 49 (>=30).
        res = self.client.get("/api/students/STU24598/career-guidance")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        pref = data["placement_outcome_reference"]
        self.assertEqual(pref["band_delta"], 20)
        self.assertGreaterEqual(pref["peer_count"], 30)
        self.assertEqual(pref["insufficient_peer_data"], False)
        self.assertIsNotNone(pref["placement_rate_pct"])

        # STU04531: Score 28.8 (Electronics Tier 1). Peer count at ±10 is 9 (<30), ±15 is 47 (>=30).
        res2 = self.client.get("/api/students/STU04531/career-guidance")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        pref2 = data2["placement_outcome_reference"]
        self.assertEqual(pref2["band_delta"], 15)
        self.assertGreaterEqual(pref2["peer_count"], 30)
        self.assertEqual(pref2["insufficient_peer_data"], False)

    def test_genai_endpoints(self):
        # 1. At-Risk Brief
        res_atrisk = self.client.get("/api/genai/atrisk-brief/STU00001")
        self.assertEqual(res_atrisk.status_code, 200)
        data_atrisk = res_atrisk.json()
        self.assertEqual(data_atrisk["student_id"], "STU00001")
        self.assertIn("brief_text", data_atrisk)
        self.assertIn("45%", data_atrisk["brief_text"])
        self.assertIn("model_probability", data_atrisk)
        self.assertIn("model_top_factor", data_atrisk)

        # 2. Performance Summary
        res_perf = self.client.get("/api/genai/performance-summary/STU00001")
        self.assertEqual(res_perf.status_code, 200)
        data_perf = res_perf.json()
        self.assertEqual(data_perf["student_id"], "STU00001")
        self.assertIn("summary_text", data_perf)
        self.assertTrue("21%" in data_perf["summary_text"] or "0.21" in data_perf["summary_text"])
        self.assertIn("current_cgpa", data_perf)
        self.assertIn("predicted_cgpa", data_perf)

        # 3. Career Guidance Narrative
        res_career = self.client.get("/api/genai/career-guidance/STU00001")
        self.assertEqual(res_career.status_code, 200)
        data_career = res_career.json()
        self.assertEqual(data_career["student_id"], "STU00001")
        self.assertIn("narrative_text", data_career)
        self.assertIn("career_readiness_score", data_career)
        self.assertIn("peer_avg", data_career)

        # 4. Cache test: repeat call returns cached response
        res_cached = self.client.get("/api/genai/atrisk-brief/STU00001")
        self.assertEqual(res_cached.status_code, 200)
        self.assertEqual(res_cached.json()["generated_at"], data_atrisk["generated_at"])

        # 5. Non-existent student returns 404
        not_found = self.client.get("/api/genai/atrisk-brief/STU99999999")
        self.assertEqual(not_found.status_code, 404)

    def test_pipeline_status_endpoint(self):
        """
        Verify live pipeline monitoring endpoint returns complete health status across all 7 stages.
        """
        res = self.client.get("/api/pipeline/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Overall summary
        self.assertEqual(data["overall_status"], "healthy")
        self.assertEqual(data["healthy_stages_count"], 7)
        self.assertEqual(data["total_stages_count"], 7)
        self.assertEqual(data["status_summary"], "7/7 Stages Operational")
        self.assertEqual(len(data["stages"]), 7)

        stage_map = {s["stage_id"]: s for s in data["stages"]}

        # Stage 1: Data Sources
        s1 = stage_map["sources"]
        self.assertEqual(s1["status"], "healthy")
        self.assertEqual(s1["details"]["total_files"], 6)
        self.assertEqual(s1["details"]["healthy_files"], 6)
        self.assertEqual(s1["details"]["total_raw_records"], 70000)

        # Stage 2: Data Ingestion
        s2 = stage_map["ingestion"]
        self.assertEqual(s2["status"], "healthy")
        self.assertEqual(s2["details"]["sources_validated"], 6)
        self.assertEqual(s2["details"]["sources_passed"], 6)

        # Stage 3: Data Cleaning (10k duplicates pruned)
        s3 = stage_map["cleaning"]
        self.assertEqual(s3["status"], "healthy")
        self.assertEqual(s3["details"]["total_duplicates_pruned"], 10000)
        self.assertEqual(s3["details"]["kundan_dedup_count"], 10000)
        self.assertEqual(len(s3["details"]["datasets"]), 6)

        # Stage 4: Data Stitching (25k rows, 116 cols, 5 match cohorts)
        s4 = stage_map["stitching"]
        self.assertEqual(s4["status"], "healthy")
        self.assertEqual(s4["details"]["master_student_rows"], 25000)
        self.assertEqual(s4["details"]["column_count"], 116)
        cov = s4["details"]["match_coverage"]
        self.assertEqual(cov["suvidya"]["matched_students"], 5000)
        self.assertEqual(cov["kundan"]["matched_students"], 15000)
        self.assertEqual(cov["sehaj"]["matched_students"], 2000)
        self.assertEqual(cov["navin"]["matched_students"], 1000)
        self.assertEqual(cov["sakhare"]["matched_students"], 12000)

        # Stage 5: Transformation & Splits (Class balance & 80/20 train/test splits)
        s5 = stage_map["transformation"]
        self.assertEqual(s5["status"], "healthy")
        splits = s5["details"]["train_test_splits"]
        self.assertEqual(splits["model1_train_rows"], 20000)
        self.assertEqual(splits["model1_test_rows"], 5000)
        self.assertEqual(splits["model2_train_rows"], 20000)
        self.assertEqual(splits["model2_test_rows"], 5000)
        self.assertAlmostEqual(s5["details"]["class_balance"]["at_risk_class_pct"], 31.9, delta=0.5)

        # Stage 6: Data Warehouse (180k rows across 4 star schema tables)
        s6 = stage_map["warehouse"]
        self.assertEqual(s6["status"], "healthy")
        wh_tbls = s6["details"]["tables"]
        self.assertEqual(wh_tbls["dim_student"], 25000)
        self.assertEqual(wh_tbls["fact_performance"], 105000)
        self.assertEqual(wh_tbls["fact_lifestyle"], 25000)
        self.assertEqual(wh_tbls["fact_career"], 25000)
        self.assertEqual(s6["details"]["total_warehouse_rows"], 180000)

        # Stage 7: Analytics, ML & GenAI
        s7 = stage_map["analytics"]
        self.assertEqual(s7["status"], "healthy")
        m1 = s7["details"]["model1_performance"]
        self.assertEqual(m1["status"], "LOADED")
        self.assertAlmostEqual(m1["r2_score"], 0.21, delta=0.05)
        self.assertIn("Directional Signal Only", m1["limitation_badge"])

        m2 = s7["details"]["model2_atrisk"]
        self.assertEqual(m2["status"], "LOADED")
        self.assertAlmostEqual(m2["recall_class1"], 0.45, delta=0.05)
        self.assertIn("Lifestyle Early Warning", m2["limitation_badge"])
        self.assertTrue(s7["details"]["genai_status"]["fallbacks_ready"])


if __name__ == "__main__":
    unittest.main()


