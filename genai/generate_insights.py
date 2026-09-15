"""
Campus360 — GenAI Student Insights & Mentor Intervention Generator
Generates faculty-facing personalized summaries combining holistic student data
and machine learning predictions.
Primary Provider: Google Gemini (gemini-3.6-flash)
Fallback Provider: Groq (qwen/qwen3.8-27b)
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import joblib

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import (
    WAREHOUSE_DB_PATH,
    MODEL_1_PATH,
    MODEL_2_PATH,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    GENAI_LOG_PATH,
    get_db_connection,
)


def log_genai_interaction(student_id: str, provider: str, model_name: str, prompt: str, response: str):
    """Appends full prompt and response to logs/genai_prompts.log."""
    GENAI_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    log_entry = (
        f"\n{'=' * 80}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"STUDENT_ID: {student_id}\n"
        f"PROVIDER: {provider} | MODEL: {model_name}\n"
        f"{'-' * 80}\n"
        f"PROMPT:\n{prompt}\n"
        f"{'-' * 80}\n"
        f"RESPONSE:\n{response}\n"
        f"{'=' * 80}\n"
    )
    with open(GENAI_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)


def normalize_student_id(raw_id: str) -> str:
    """Normalizes student ID inputs (e.g., 'S900', '900', 's100000') into standard S10xxxx format."""
    if not raw_id:
        return ""
    cleaned = str(raw_id).strip().upper()
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if not digits:
        return cleaned
    val = int(digits)
    if len(digits) <= 4 and 0 <= val <= 9999:
        return f"S10{val:04d}"
    if len(digits) == 5:
        return f"S{val:06d}"
    if len(digits) == 6:
        return f"S{digits}"
    return cleaned


def get_student_record(student_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full student record from SQLite warehouse."""
    student_id = normalize_student_id(student_id)
    conn = get_db_connection()
    try:
        query = "SELECT * FROM student_360_view WHERE student_id = ?;"
        cursor = conn.cursor()
        cursor.execute(query, (student_id,))
        row = cursor.fetchone()
        if not row:
            # Fallback to student_master_stitched
            query2 = "SELECT * FROM student_master_stitched WHERE student_id = ?;"
            cursor.execute(query2, (student_id,))
            row = cursor.fetchone()

        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_ml_predictions(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Runs Model 1 (Marks Regression) and Model 2 (Risk Classifier) on the student record."""
    preds = {
        "predicted_marks": None,
        "predicted_risk_prob": None,
        "risk_classification": "Unknown",
    }

    # Model 1
    if MODEL_1_PATH.exists():
        try:
            m1 = joblib.load(MODEL_1_PATH)
            feat_cols = getattr(m1, "feature_names_in_", None)
            if feat_cols is not None:
                row_dict = {}
                for col in feat_cols:
                    val = student_data.get(col)
                    if val is None and col == "backlogs":
                        val = student_data.get("backlog_history", 0.0)
                    elif val is None and col == "backlog_history":
                        val = student_data.get("backlogs", 0.0)
                    row_dict[col] = float(val) if val is not None else 0.0
                X1 = pd.DataFrame([row_dict])[feat_cols]
                preds["predicted_marks"] = round(float(m1.predict(X1)[0]), 2)
        except Exception as e:
            print(f"[ML WARNING] Model 1 prediction error: {e}")

    # Model 2
    if MODEL_2_PATH.exists():
        try:
            m2 = joblib.load(MODEL_2_PATH)
            feat_cols = getattr(m2, "feature_names_in_", None)
            if feat_cols is not None:
                row_dict = {}
                for col in feat_cols:
                    val = student_data.get(col)
                    if val is None and col == "backlog_history":
                        val = student_data.get("backlogs", 0.0)
                    elif val is None and col == "backlogs":
                        val = student_data.get("backlog_history", 0.0)
                    row_dict[col] = float(val) if val is not None else 0.0
                X2 = pd.DataFrame([row_dict])[feat_cols]
                prob = float(m2.predict_proba(X2)[0, 1])
                preds["predicted_risk_prob"] = round(prob, 3)
                # Calibrated threshold for screening recall >= 85% is ~0.416
                preds["risk_classification"] = "At-Risk (High Priority)" if prob >= 0.416 else "On-Track"
        except Exception as e:
            print(f"[ML WARNING] Model 2 prediction error: {e}")

    return preds


def build_faculty_prompt(student_id: str, record: Dict[str, Any], ml_preds: Dict[str, Any]) -> str:
    """Builds a structured prompt for the LLM."""
    prompt = f"""You are an expert university academic advisor and student success counselor analyzing a comprehensive student dossier.

STUDENT PROFILE ({student_id}):
- Current CGPA: {record.get('cgpa', 'N/A')} / 10.0 (Previous CGPA: {record.get('previous_cgpa', 'N/A')})
- Historical Semester Percentage: {record.get('previous_semester_percentage', 'N/A')}%
- Active Backlogs: {record.get('backlogs', 0)} | Failed Subjects: {record.get('failed_subjects', 0)}
- Performance Band: {record.get('performance_band', 'N/A')}
- Attendance: {record.get('attendance_percentage', 'N/A')}%
- Daily Study Hours: {record.get('study_hours_daily', 'N/A')} hrs | Self Learning: {record.get('self_learning_hours', 'N/A')} hrs

LIFESTYLE & PSYCHOLOGICAL WELLNESS:
- Sleep Hours: {record.get('sleep_hours', 'N/A')} hrs/night
- Daily Screen Time: {record.get('screen_time', 'N/A')} hrs | Gaming: {record.get('gaming_hours', 'N/A')} hrs
- Stress Level: {record.get('stress_level', 'N/A')} / 10 | Burnout Score: {record.get('burnout_score', 'N/A')} / 100
- Wellness Score: {record.get('wellness_score', 'N/A')} / 100 | Motivation Level: {record.get('motivation_level', 'N/A')} / 10

CAREER READINESS & ASPIRATIONS:
- Preferred Domain: {record.get('preferred_domain', 'N/A')} | Career Goal: {record.get('career_goal', 'N/A')}
- Resume Score: {record.get('resume_score', 'N/A')} / 100 | Communication: {record.get('communication_skills', 'N/A')} / 100
- Technical Projects: {record.get('development_projects_count', 0)} | Hackathons: {record.get('hackathons_participated', 0)} | GitHub Repos: {record.get('git_hub_repos', 0)}

PREDICTIVE ML FORECASTS:
- Model 1 (Predicted Next Semester Marks): {ml_preds.get('predicted_marks', 'N/A')} / 100
- Model 2 (Screening At-Risk Probability): {ml_preds.get('predicted_risk_prob', 'N/A')} ({ml_preds.get('risk_classification', 'N/A')})

INSTRUCTIONS FOR FACULTY/MENTOR SUMMARY:
Write a concise, professional, and empathetic 4-section briefing for the student's mentor:
1. Executive Assessment: Overall diagnosis of academic health and risk status.
2. Critical Risk Factors & Behavioral Flags: Specific pain points (e.g. stress, attendance drops, sleep deficits).
3. Strengths & Bright Spots: Natural capabilities, technical interests, or strong coursework metrics.
4. Actionable Mentorship Intervention: 3 concrete steps the faculty advisor should take in the next 14 days.

Format with clear markdown headings and bullet points. Keep it professional, empathetic, and actionable."""
    return prompt


def call_llm(prompt: str, student_id: str) -> Dict[str, str]:
    """
    Calls Gemini as primary provider with automatic fallback to Groq.
    """
    # ── 1. Try Gemini (Primary) ────────────────────────────────────────────────
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            text_resp = response.text.strip()
            log_genai_interaction(student_id, "Google Gemini", "gemini-3.6-flash", prompt, text_resp)
            return {
                "provider": "Google Gemini",
                "model": "gemini-3.6-flash",
                "insights": text_resp,
                "status": "success",
            }
        except Exception as e:
            print(f"[GENAI WARNING] Gemini call failed: {e}. Falling back to Groq...")

    # ── 2. Try Groq (Fallback) ─────────────────────────────────────────────────
    if GROQ_API_KEY:
        try:
            from groq import Groq
            groq_client = Groq(api_key=GROQ_API_KEY)
            completion = groq_client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": "You are a university student academic advisor providing structured faculty intervention briefs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            text_resp = completion.choices[0].message.content.strip()
            log_genai_interaction(student_id, "Groq", "qwen/qwen3.8-27b", prompt, text_resp)
            return {
                "provider": "Groq",
                "model": "qwen/qwen3.8-27b",
                "insights": text_resp,
                "status": "success",
            }
        except Exception as e:
            print(f"[GENAI WARNING] Groq fallback failed: {e}")

    # ── 3. Deterministic Local Fallback (if both APIs fail or offline) ─────────
    offline_summary = (
        f"### 📋 Academic Advisory Briefing for {student_id} (Offline Mode)\n\n"
        f"**1. Executive Assessment:** Student presents with current CGPA of {prompt.split('Current CGPA: ')[1].split(' ')[0]}.\n"
        f"**2. Risk Indicators:** Automated screening indicates intervention recommended.\n"
        f"**3. Suggested Action:** Schedule one-on-one advising to review study schedules and psychological wellness."
    )
    log_genai_interaction(student_id, "Local Fallback", "heuristic", prompt, offline_summary)
    return {
        "provider": "Local Fallback (Offline)",
        "model": "rule-based-heuristic",
        "insights": offline_summary,
        "status": "fallback",
    }


def generate_student_insight(student_id: str) -> Dict[str, Any]:
    """End-to-end insight generation for a single student."""
    student_id = normalize_student_id(student_id)
    record = get_student_record(student_id)
    if not record:
        raise ValueError(f"Student ID '{student_id}' not found in warehouse.")

    ml_preds = get_ml_predictions(record)
    prompt = build_faculty_prompt(student_id, record, ml_preds)
    llm_result = call_llm(prompt, student_id)

    return {
        "student_id": student_id,
        "student_record": record,
        "predictions": ml_preds,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "insights": llm_result["insights"],
        "status": llm_result["status"],
    }


def main():
    student_id = sys.argv[1].upper() if len(sys.argv) > 1 else "S100000"
    print("=" * 80)
    print(f"  CAMPUS360 GENAI ADVISORY INSIGHTS GENERATOR — {student_id}")
    print("=" * 80)

    result = generate_student_insight(student_id)

    print(f"\n[AI PROVIDER]: {result['provider']} ({result['model']})")
    print(f"[ML FORECASTS]: Predicted Marks = {result['predictions']['predicted_marks']} | Risk Prob = {result['predictions']['predicted_risk_prob']}")
    print("\n" + "=" * 80)
    print(result["insights"])
    print("=" * 80)
    print(f"\n[LOG]: Full audit prompt & response recorded in: {GENAI_LOG_PATH}\n")


if __name__ == "__main__":
    main()
