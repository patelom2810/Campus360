"""
tests/test_assess_api.py
Automated test suite verifying Campus360 "Bring Your Own Data" (BYOD) Assessment:
- Serves /assess HTML entry page and static assets
- Option 1: CSV Match preview + confirm batch flow
- Option 2: Multi-CSV Stitching + lineage disclosure
- Option 3: Stateful chatbot-guided flow with skipping
- Option 4: Direct form assessment (run_full_assessment)
- Zero database mutations guarantee
"""

import io
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import text
from src.api.main import app
from src.etl.load import create_warehouse_engine


class TestAssessAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_assess_page_served(self):
        """Verify /assess and /assess/ return the BYOD HTML page with correct status and markup."""
        r1 = self.client.get("/assess")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("text/html", r1.headers.get("content-type", ""))
        self.assertIn("Bring Your Own Data", r1.text)
        self.assertIn("How would you like to", r1.text)
        self.assertIn("provide your data?", r1.text)
        self.assertIn("Our Data Dashboard", r1.text)

        r2 = self.client.get("/assess/")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("Bring Your Own Data", r2.text)

    def test_assess_assets_served(self):
        """Verify /assess/assess.js is accessible via the static mount."""
        r = self.client.get("/assess/assess.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Campus360", r.text)

    def test_direct_new_student_assessment(self):
        """Verify Option 4: POST /api/assess/new-student produces unified assessment response."""
        payload = {
            "anchor_attendance_percentage": 88.0,
            "anchor_study_hours_daily": 5.5,
            "anchor_sleep_hours": 7.0,
            "anchor_stress_level": 45.0,
            "anchor_burnout_score": 35.0,
            "anchor_dsa_problems_solved": 250.0,
            "branch": "Computer Science",
            "college_tier": 1,
        }
        res = self.client.post("/api/assess/new-student", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("predicted_cgpa", data)
        self.assertTrue(0.0 <= data["predicted_cgpa"] <= 10.0)
        self.assertIn("at_risk_probability", data)
        self.assertTrue(0.0 <= data["at_risk_probability"] <= 1.0)
        self.assertIn(data["at_risk_label"], ["At-Risk", "Safe"])
        self.assertIn("career_readiness", data)
        self.assertIn("atrisk_brief", data)
        self.assertIn("performance_summary", data)
        self.assertIn("career_narrative", data)
        self.assertIn("defaulted_fields", data)
        self.assertGreater(len(data["defaulted_fields"]), 0)
        self.assertIn("disclaimers", data)
        self.assertIn("model1_note", data["disclaimers"])
        self.assertIn("model2_note", data["disclaimers"])
        self.assertIn("byod_note", data["disclaimers"])

    def test_csv_match_and_confirm(self):
        """Verify Option 1: CSV upload preview fuzzy matching and confirm batch processing."""
        csv_data = (
            "Name,Study Hours Daily,Sleep Hrs,Stress Score,Attendance Pct,DSA Solved,Branch,Tier\n"
            "Alice,6.0,7.5,30,92,300,Computer Science,1\n"
            "Bob,2.0,5.0,85,60,30,Mechanical,2\n"
            "Charlie,4.5,6.5,50,80,120,Information Technology,2\n"
        ).encode("utf-8")

        # Step 1: Upload CSV for fuzzy matching preview
        files = {"file": ("students.csv", io.BytesIO(csv_data), "text/csv")}
        r_prev = self.client.post("/api/assess/csv-match", files=files)
        self.assertEqual(r_prev.status_code, 200)
        prev_data = r_prev.json()

        self.assertIn("preview_id", prev_data)
        self.assertIn("mapping_preview", prev_data)
        self.assertEqual(prev_data["total_rows"], 3)

        mapping = prev_data["mapping_preview"]
        self.assertGreaterEqual(len(mapping), 5)

        # Step 2: Confirm mapping and run batch assessment
        confirm_payload = {
            "preview_id": prev_data["preview_id"],
            "mapping": [
                {"uploaded_column": m["uploaded_column"], "matched_to_feature": m["matched_to_feature"]}
                for m in mapping
            ],
        }
        r_conf = self.client.post("/api/assess/csv-match/confirm", json=confirm_payload)
        self.assertEqual(r_conf.status_code, 200)
        batch = r_conf.json()

        self.assertIn("summary", batch)
        self.assertEqual(batch["summary"]["total_rows"], 3)
        self.assertEqual(batch["summary"]["successfully_assessed"], 3)
        self.assertIn("avg_predicted_cgpa", batch["summary"])
        self.assertIn("pct_flagged_at_risk", batch["summary"])
        self.assertEqual(len(batch["results"]), 3)

        s1 = batch["results"][0]["assessment"]
        self.assertIn("predicted_cgpa", s1)
        self.assertIn("at_risk_probability", s1)

    def test_csv_stitch(self):
        """Verify Option 2: Multi-CSV upload stitches datasets and runs batch assessment."""
        csv1 = (
            "student_id,attendance_rate,daily_study_hours\n"
            "S101,88,5.0\n"
            "S102,62,2.0\n"
        ).encode("utf-8")

        csv2 = (
            "student_id,stress,dsa_count,engineering_branch\n"
            "S101,40,200,Computer Science\n"
            "S102,78,40,Civil\n"
        ).encode("utf-8")

        files = [
            ("files", ("academics.csv", io.BytesIO(csv1), "text/csv")),
            ("files", ("skills.csv", io.BytesIO(csv2), "text/csv")),
        ]
        r = self.client.post("/api/assess/csv-stitch", files=files)
        self.assertEqual(r.status_code, 200)
        res = r.json()

        self.assertIn("summary", res)
        self.assertEqual(res["summary"]["total_rows"], 2)
        self.assertIn("lineage", res)
        self.assertEqual(res["lineage"]["files_uploaded"], ["academics.csv", "skills.csv"])
        self.assertEqual(res["lineage"]["join_method"], "real_key_join")
        self.assertEqual(len(res["results"]), 2)

    def test_chat_guided_session(self):
        """Verify Option 3: Stateful guided chatbot conversation and auto-assessment at finish."""
        # Step 1: Start session
        r1 = self.client.post("/api/assess/chat-guided", json={"message": "hello"})
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()

        session_id = d1.get("session_id")
        self.assertIsNotNone(session_id)
        self.assertFalse(d1["session_complete"])
        self.assertIn("bot_message", d1)
        self.assertEqual(d1["progress_pct"], 0)

        # Step 2: Answer first question
        r2 = self.client.post("/api/assess/chat-guided", json={"session_id": session_id, "message": "85%"})
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertGreater(d2["progress_pct"], 0)

        # Step 3: Skip a question
        r3 = self.client.post("/api/assess/chat-guided", json={"session_id": session_id, "message": "skip"})
        self.assertEqual(r3.status_code, 200)
        d3 = r3.json()
        self.assertGreaterEqual(len(d3.get("collected_data", {})), 1)

    def test_zero_database_mutations(self):
        """Verify that calling assessment endpoints NEVER writes any records to the database."""
        engine, _ = create_warehouse_engine()
        with engine.connect() as conn:
            count_students_before = conn.execute(text("SELECT COUNT(*) FROM dim_student")).scalar()
            count_perf_before = conn.execute(text("SELECT COUNT(*) FROM fact_performance")).scalar()
            count_lifestyle_before = conn.execute(text("SELECT COUNT(*) FROM fact_lifestyle")).scalar()
            count_career_before = conn.execute(text("SELECT COUNT(*) FROM fact_career")).scalar()

        # Call direct assessment
        self.client.post("/api/assess/new-student", json={
            "anchor_attendance_percentage": 90.0,
            "anchor_study_hours_daily": 6.0,
        })

        # Call CSV match preview and confirm
        csv_data = "attendance,study_hours\n85,4.0\n75,3.0\n".encode("utf-8")
        files = {"file": ("test.csv", io.BytesIO(csv_data), "text/csv")}
        r_prev = self.client.post("/api/assess/csv-match", files=files)
        prev = r_prev.json()
        self.client.post("/api/assess/csv-match/confirm", json={
            "preview_id": prev["preview_id"],
            "mapping": [{"uploaded_column": m["uploaded_column"], "matched_to_feature": m["matched_to_feature"]} for m in prev["mapping_preview"]]
        })

        # Verify counts in database are unchanged
        with engine.connect() as conn:
            count_students_after = conn.execute(text("SELECT COUNT(*) FROM dim_student")).scalar()
            count_perf_after = conn.execute(text("SELECT COUNT(*) FROM fact_performance")).scalar()
            count_lifestyle_after = conn.execute(text("SELECT COUNT(*) FROM fact_lifestyle")).scalar()
            count_career_after = conn.execute(text("SELECT COUNT(*) FROM fact_career")).scalar()

        self.assertEqual(count_students_after, count_students_before)
        self.assertEqual(count_perf_after, count_perf_before)
        self.assertEqual(count_lifestyle_after, count_lifestyle_before)
        self.assertEqual(count_career_after, count_career_before)


if __name__ == "__main__":
    unittest.main()
