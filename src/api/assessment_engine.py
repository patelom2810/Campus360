"""
src/api/assessment_engine.py
Shared "Bring Your Own Data" assessment engine for Campus360.

run_full_assessment(student_data: dict) -> dict

Accepts any partial dict of student fields, fills missing values with
population medians, engineers the 4 interaction features, runs both
ML models, computes Career Readiness Score, calls all 3 GenAI functions
via data-dict bypass (no DB lookup), and returns a unified response shape.

This function is deliberately stateless and NEVER writes to any database.
All 4 BYOD input options (CSV, multi-CSV, chat, direct form) converge here.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

# ── Path Setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MODELS_DIR = BASE_DIR / "models"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

logger = logging.getLogger("assessment_engine")

# ── Production Feature Schema ─────────────────────────────────────────────────
# 24 raw input fields that the models accept (excluding the 4 engineered ones
# which are computed below).  All are optional from the caller; missing ones
# are filled from the training-set population medians.
RAW_FEATURE_FIELDS: List[str] = [
    "anchor_attendance_percentage",
    "anchor_study_hours_daily",
    "anchor_self_learning_hours",
    "anchor_sleep_hours",
    "anchor_screen_time",
    "anchor_gaming_hours",
    "anchor_stress_level",
    "anchor_burnout_score",
    "anchor_backlog_history",
    "anchor_dsa_problems_solved",
    "anchor_internships_completed",
    "anchor_motivation_level",
    "anchor_family_income_lpa",
    "anchor_resume_score",
    "anchor_communication_skills",
    "anchor_aptitude_score",
    "anchor_mock_interview_score",
    "anchor_hackathons_participated",
    "anchor_development_projects_count",
    "anchor_ai_ml_projects",
    "anchor_git_hub_repos",
    "anchor_ai_tool_usage_frequency",
    "anchor_prompt_engineering_skill",
    "anchor_adaptability_score",
    # Model 2 also needs this lifestyle field:
    "anchor_gym_frequency",
]

# The 4 engineered features (computed from raw fields — never taken from input)
ENGINEERED_FEATURES = ["effort_score", "screen_to_study_ratio", "wellness_score", "project_activity"]

# Career Readiness Engine — weights and column mapping
_CAREER_WEIGHTS = {
    "dsa": 0.25,
    "internships": 0.20,
    "communication": 0.15,
    "aptitude": 0.15,
    "projects": 0.15,
    "mock_interview": 0.10,
}
_CAREER_COL_MAP = {
    "dsa": "anchor_dsa_problems_solved",
    "internships": "anchor_internships_completed",
    "communication": "anchor_communication_skills",
    "aptitude": "anchor_aptitude_score",
    "projects": "_projects_total",
    "mock_interview": "anchor_mock_interview_score",
}
_CAREER_LABELS = {
    "dsa": "DSA Problem Solving",
    "internships": "Industry Internships",
    "communication": "Communication Skills",
    "aptitude": "Aptitude Score",
    "projects": "Development & AI Projects",
    "mock_interview": "Mock Interview Performance",
}
_CAREER_SUGGESTIONS = {
    "dsa": "Coding practice is your biggest gap versus peers — prioritize DSA problem-solving on platforms like LeetCode or HackerRank.",
    "internships": "You have fewer internships than peers in your branch — consider applying this semester via campus placement cell or internship portals.",
    "communication": "Communication skills lag behind your technical profile — consider mock interview sessions, group discussions, or a communication workshop.",
    "aptitude": "Aptitude scores are your relative weak point — targeted quantitative reasoning and logical practice can significantly boost this.",
    "projects": "Project portfolio is thin compared to branch peers — build one applied project (web app, ML model, or open-source contribution) this month.",
    "mock_interview": "Mock interview performance is your lowest-ranked skill — schedule structured practice sessions with seniors or career services.",
}

# ── Lazy-loaded caches (shared within a process, reset on restart) ─────────────
_MODEL1_CACHE: Optional[Tuple[Any, dict, dict]] = None
_MODEL2_CACHE: Optional[Tuple[Any, dict]] = None
_POPULATION_CACHE: Optional[pd.DataFrame] = None
_MEDIANS_CACHE: Optional[Dict[str, float]] = None


def _get_model1() -> Tuple[Any, dict, dict]:
    """Loads and caches Model 1 (GradientBoostingRegressor) with its medians."""
    global _MODEL1_CACHE
    if _MODEL1_CACHE is not None:
        return _MODEL1_CACHE
    model_path = MODELS_DIR / "model1_performance_predictor.joblib"
    metrics_path = MODELS_DIR / "model1_performance_metrics.json"
    if not model_path.exists() or not metrics_path.exists():
        raise RuntimeError("Model 1 artifacts missing — cannot run assessment")
    model = joblib.load(model_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    train_path = PROCESSED_DIR / "model1_performance_train.csv"
    medians: Dict[str, float] = {}
    if train_path.exists():
        train_df = pd.read_csv(train_path)
        medians = {
            col: float(train_df[col].median())
            for col in metrics["features"]
            if col in train_df.columns
        }
    _MODEL1_CACHE = (model, metrics, medians)
    return _MODEL1_CACHE


def _get_model2() -> Tuple[Any, dict]:
    """Loads and caches Model 2 (RandomForestClassifier)."""
    global _MODEL2_CACHE
    if _MODEL2_CACHE is not None:
        return _MODEL2_CACHE
    model_path = MODELS_DIR / "model2_atrisk_classifier.joblib"
    metrics_path = MODELS_DIR / "model2_atrisk_metrics.json"
    if not model_path.exists() or not metrics_path.exists():
        raise RuntimeError("Model 2 artifacts missing — cannot run assessment")
    model = joblib.load(model_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    _MODEL2_CACHE = (model, metrics)
    return _MODEL2_CACHE


def _get_population() -> pd.DataFrame:
    """Loads and caches the student master wide CSV for population normalization."""
    global _POPULATION_CACHE
    if _POPULATION_CACHE is not None:
        return _POPULATION_CACHE
    wide_path = PROCESSED_DIR / "student_master_wide.csv"
    if not wide_path.exists():
        raise RuntimeError("student_master_wide.csv missing — cannot compute Career Readiness")
    df = pd.read_csv(wide_path)
    df["_projects_total"] = (
        df["anchor_development_projects_count"].fillna(0)
        + df["anchor_ai_ml_projects"].fillna(0)
    )
    _POPULATION_CACHE = df
    return _POPULATION_CACHE


def _get_all_medians() -> Dict[str, float]:
    """Returns population medians for all raw feature fields (for default-filling)."""
    global _MEDIANS_CACHE
    if _MEDIANS_CACHE is not None:
        return _MEDIANS_CACHE
    # Prefer training-set medians (same distribution the models saw)
    train_path = PROCESSED_DIR / "model1_performance_train.csv"
    if train_path.exists():
        df = pd.read_csv(train_path)
        medians = {
            col: float(df[col].median())
            for col in RAW_FEATURE_FIELDS
            if col in df.columns
        }
    else:
        # Hard-coded population-level fallbacks if training CSV is unavailable
        medians = {
            "anchor_attendance_percentage": 80.0,
            "anchor_study_hours_daily": 4.0,
            "anchor_self_learning_hours": 1.5,
            "anchor_sleep_hours": 7.0,
            "anchor_screen_time": 5.0,
            "anchor_gaming_hours": 1.0,
            "anchor_stress_level": 54.0,
            "anchor_burnout_score": 44.0,
            "anchor_backlog_history": 0.0,
            "anchor_dsa_problems_solved": 120.0,
            "anchor_internships_completed": 1.0,
            "anchor_motivation_level": 6.0,
            "anchor_family_income_lpa": 8.0,
            "anchor_resume_score": 60.0,
            "anchor_communication_skills": 70.0,
            "anchor_aptitude_score": 65.0,
            "anchor_mock_interview_score": 60.0,
            "anchor_hackathons_participated": 1.0,
            "anchor_development_projects_count": 2.0,
            "anchor_ai_ml_projects": 1.0,
            "anchor_git_hub_repos": 8.0,
            "anchor_ai_tool_usage_frequency": 3.0,
            "anchor_prompt_engineering_skill": 5.0,
            "anchor_adaptability_score": 6.0,
            "anchor_gym_frequency": 3.0,
        }
    _MEDIANS_CACHE = medians
    return _MEDIANS_CACHE


# ── Engineered Feature Computation ───────────────────────────────────────────
def _compute_engineered_features(row: Dict[str, float]) -> Dict[str, float]:
    """
    Computes the 4 production engineered interaction features from filled raw fields.
    Exact same formulas as in /api/models/predict-performance and Model 2 preprocessing.
    """
    study = row.get("anchor_study_hours_daily", 4.0)
    screen = row.get("anchor_screen_time", 5.0)
    sleep = row.get("anchor_sleep_hours", 7.0)
    stress = row.get("anchor_stress_level", 54.0)
    burnout = row.get("anchor_burnout_score", 44.0)
    attendance = row.get("anchor_attendance_percentage", 80.0)
    dsa = row.get("anchor_dsa_problems_solved", 120.0)
    dev_projects = row.get("anchor_development_projects_count", 2.0)
    ai_projects = row.get("anchor_ai_ml_projects", 1.0)
    github = row.get("anchor_git_hub_repos", 8.0)

    return {
        "screen_to_study_ratio": screen / (study + 1.0),
        "wellness_score": sleep - (stress / 10.0) - (burnout / 10.0),
        "effort_score": study + (attendance / 10.0) + (dsa / 100.0),
        "project_activity": dev_projects + ai_projects + (github / 5.0),
    }


# ── Career Readiness Engine ───────────────────────────────────────────────────
def _compute_career_readiness(
    student_row: Dict[str, float],
    branch: Optional[str],
    tier: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    Computes Career Readiness Score for a BYOD student.
    Uses the same 6-component weighted composite as the production endpoint,
    normalized against the existing population from student_master_wide.csv.
    Returns None if the population CSV is unavailable.
    """
    try:
        pop_df = _get_population()
    except RuntimeError:
        return None

    # Build a _projects_total field for the student
    dev = student_row.get("anchor_development_projects_count", 0.0)
    ai_proj = student_row.get("anchor_ai_ml_projects", 0.0)
    student_row_extended = dict(student_row)
    student_row_extended["_projects_total"] = dev + ai_proj

    # Step 1: Normalize each component against population min/max
    component_norms: Dict[str, float] = {}
    for key, col in _CAREER_COL_MAP.items():
        raw_val = float(student_row_extended.get(col, 0.0))
        pop_min = float(pop_df[col].min())
        pop_max = float(pop_df[col].max())
        rng = pop_max - pop_min
        norm = (raw_val - pop_min) / rng * 100.0 if rng > 0 else 50.0
        component_norms[key] = round(float(np.clip(norm, 0.0, 100.0)), 2)

    # Step 2: Weighted composite
    readiness_score = sum(
        component_norms[k] * w for k, w in _CAREER_WEIGHTS.items()
    )
    readiness_score = round(float(np.clip(readiness_score, 0.0, 100.0)), 1)

    # Step 3: Peer benchmark if branch is known
    peer_avg_score: Optional[float] = None
    peer_group_label = "All Students"
    if branch:
        peer_df = pop_df[pop_df["anchor_branch"] == branch].copy()
        if tier is not None and len(peer_df) >= 2:
            tier_df = peer_df[peer_df["anchor_college_tier"] == tier]
            if len(tier_df) >= 2:
                peer_df = tier_df
                peer_group_label = f"{branch} · Tier {tier}"
            else:
                peer_group_label = branch
        else:
            peer_group_label = branch

        def _score_row(r: pd.Series) -> float:
            s = 0.0
            for k, col in _CAREER_COL_MAP.items():
                rv = float(r[col]) if pd.notna(r[col]) else 0.0
                pm = float(pop_df[col].min())
                px = float(pop_df[col].max())
                rng = px - pm
                n = (rv - pm) / rng * 100.0 if rng > 0 else 50.0
                s += float(np.clip(n, 0.0, 100.0)) * _CAREER_WEIGHTS[k]
            return round(float(np.clip(s, 0.0, 100.0)), 1)

        if len(peer_df) >= 1:
            peer_avg_score = round(float(peer_df.apply(_score_row, axis=1).mean()), 1)

    # Step 4: Skill gap breakdown (percentile within branch population)
    skill_gaps: List[Dict[str, Any]] = []
    ref_df = pop_df[pop_df["anchor_branch"] == branch] if branch else pop_df
    for key, col in _CAREER_COL_MAP.items():
        stu_val = float(student_row_extended.get(col, 0.0))
        branch_vals = ref_df[col].dropna().values
        percentile = float(np.mean(branch_vals <= stu_val) * 100.0) if len(branch_vals) else 50.0
        skill_gaps.append({
            "component": key,
            "label": _CAREER_LABELS[key],
            "student_raw": round(stu_val, 1),
            "student_normalized": component_norms[key],
            "percentile_in_branch": round(percentile, 1),
        })
    skill_gaps.sort(key=lambda x: x["percentile_in_branch"])

    lowest_key = skill_gaps[0]["component"]
    suggested_focus = _CAREER_SUGGESTIONS[lowest_key]

    return {
        "career_readiness_score": readiness_score,
        "peer_benchmark": {
            "peer_avg_readiness": peer_avg_score,
            "peer_group": peer_group_label,
            "note": "Peer benchmark reflects existing population in student_master_wide.csv — BYOD student is not included.",
        },
        "skill_gap_breakdown": skill_gaps,
        "suggested_focus_area": {
            "component": lowest_key,
            "label": _CAREER_LABELS[lowest_key],
            "suggestion": suggested_focus,
        },
    }


# ── Main Entry Point ──────────────────────────────────────────────────────────
def run_full_assessment(student_data: Dict[str, Any], include_genai: bool = True) -> Dict[str, Any]:
    """
    Runs the full Campus360 assessment pipeline for a single student's data dict.

    Parameters
    ----------
    student_data : dict
        Any subset of the 24 raw feature fields (plus optional 'branch', 'tier',
        'student_label' for display). Missing fields are median-filled.

    Returns
    -------
    dict with keys:
        predicted_cgpa          float  — Model 1 prediction (clipped [0, 10])
        at_risk_probability     float  — Model 2 probability (0–1)
        at_risk_label           str    — "At-Risk" | "Safe"
        career_readiness        dict | None
        atrisk_brief            dict   — GenAI brief (or fallback)
        performance_summary     dict   — GenAI summary (or fallback)
        career_narrative        dict   — GenAI narrative (or fallback)
        defaulted_fields        list   — fields that were filled with medians
        disclaimers             dict   — model calibration text
        input_echo              dict   — cleaned/filled values actually used
    """
    # ── Step 1: Fill missing raw fields with population medians ───────────────
    medians = _get_all_medians()
    filled: Dict[str, float] = {}
    defaulted_fields: List[str] = []

    for field in RAW_FEATURE_FIELDS:
        raw_val = student_data.get(field)
        if raw_val is None or (isinstance(raw_val, float) and np.isnan(raw_val)):
            filled[field] = medians.get(field, 0.0)
            defaulted_fields.append(field)
            logger.info("Defaulted field '%s' → %.2f (population median)", field, filled[field])
        else:
            try:
                filled[field] = float(raw_val)
            except (ValueError, TypeError):
                filled[field] = medians.get(field, 0.0)
                defaulted_fields.append(field)

    # ── Step 2: Compute 4 engineered interaction features ─────────────────────
    engineered = _compute_engineered_features(filled)
    full_row = {**filled, **engineered}

    # ── Step 3: Run Model 1 — CGPA Prediction ─────────────────────────────────
    model1, meta1, _ = _get_model1()
    features1: List[str] = meta1["features"]
    X1 = pd.DataFrame([{f: full_row.get(f, 0.0) for f in features1}])[features1]
    raw_cgpa = float(model1.predict(X1)[0])
    predicted_cgpa = round(float(np.clip(raw_cgpa, 0.0, 10.0)), 2)

    # ── Step 4: Run Model 2 — At-Risk Classification ──────────────────────────
    model2, meta2 = _get_model2()
    features2: List[str] = meta2["features"]
    X2 = pd.DataFrame([{f: full_row.get(f, 0.0) for f in features2}])[features2]
    at_risk_prob = round(float(model2.predict_proba(X2)[0, 1]), 4)
    threshold = float(meta2.get("decision_threshold", 0.50))
    at_risk_label = "At-Risk" if at_risk_prob >= threshold else "Safe"

    # ── Step 5: Career Readiness Engine ───────────────────────────────────────
    branch = student_data.get("branch") or student_data.get("stream_branch")
    tier_raw = student_data.get("tier") or student_data.get("college_tier")
    tier = int(tier_raw) if tier_raw is not None else None
    career_readiness = _compute_career_readiness(filled, branch, tier)

    # ── Step 6: Build GenAI-compatible payload and call all 3 functions ────────
    student_label = str(student_data.get("student_label", "BYOD-Student"))

    # Compute top contributing risk factor (same z-score logic as production)
    pos_risk_cols = {
        "anchor_burnout_score": ("Elevated Burnout", "/10"),
        "anchor_stress_level": ("High Academic Stress", "/10"),
        "anchor_screen_time": ("Excessive Screen Time", " hrs/day"),
        "anchor_gaming_hours": ("Excessive Gaming", " hrs/day"),
        "screen_to_study_ratio": ("Screen-to-Study Imbalance", " ratio"),
    }
    neg_risk_cols = {
        "anchor_sleep_hours": ("Chronic Sleep Deprivation", " hrs/night"),
        "anchor_study_hours_daily": ("Low Daily Study Hours", " hrs/day"),
        "anchor_self_learning_hours": ("Low Self-Learning Effort", " hrs/day"),
        "anchor_motivation_level": ("Low Motivation Level", "/10"),
        "anchor_adaptability_score": ("Low Adaptability Score", "/10"),
        "wellness_score": ("Depleted Wellness Index", " pts"),
    }

    # Use population medians as reference for z-score computation
    try:
        pop_df = _get_population()
        max_z = -999.0
        top_factor = "Academic Workload Imbalance"
        stu_val_str = "N/A"
        pop_avg_str = "N/A"
        for col, (desc, unit) in pos_risk_cols.items():
            if col in pop_df.columns:
                m = float(pop_df[col].mean())
                s = float(pop_df[col].std()) or 1.0
                val = full_row.get(col, m)
                z = (val - m) / s
                if z > max_z:
                    max_z = z
                    top_factor = desc
                    stu_val_str = f"{val:.1f}{unit}"
                    pop_avg_str = f"{m:.1f}{unit}"
        for col, (desc, unit) in neg_risk_cols.items():
            if col in pop_df.columns:
                m = float(pop_df[col].mean())
                s = float(pop_df[col].std()) or 1.0
                val = full_row.get(col, m)
                z = (m - val) / s
                if z > max_z:
                    max_z = z
                    top_factor = desc
                    stu_val_str = f"{val:.1f}{unit}"
                    pop_avg_str = f"{m:.1f}{unit}"
    except Exception:
        top_factor = "Academic Workload Imbalance"
        stu_val_str = "N/A"
        pop_avg_str = "N/A"

    # Build data payloads for GenAI bypass
    atrisk_payload = {
        "student_id": student_label,
        "branch": branch or "Engineering",
        "college_tier": tier or 2,
        "at_risk_label": at_risk_label,
        "probability": at_risk_prob,
        "top_factor": top_factor,
        "student_value": stu_val_str,
        "population_average": pop_avg_str,
    }

    perf_payload = {
        "student_id": student_label,
        "current_cgpa": None,  # Not known for BYOD
        "predicted_cgpa": predicted_cgpa,
        "direction": (
            "improving" if predicted_cgpa > 7.62 else
            "declining slightly" if predicted_cgpa < 7.0 else "stable"
        ),
        "top_factors": [
            {"name": "DSA Problems Solved", "student_val": f"{int(filled.get('anchor_dsa_problems_solved', 120))} problems", "pop_avg": "120 problems"},
            {"name": "Daily Study Hours", "student_val": f"{filled.get('anchor_study_hours_daily', 4.0):.1f} hrs/day", "pop_avg": "4.0 hrs/day"},
            {"name": "Communication Skills", "student_val": f"{filled.get('anchor_communication_skills', 70.0):.1f} pts", "pop_avg": "70.0 pts"},
        ],
    }

    career_payload = None
    if career_readiness:
        skill_gaps = career_readiness.get("skill_gap_breakdown", [])
        career_payload = {
            "student_id": student_label,
            "branch": branch or "Engineering",
            "college_tier": tier or 2,
            "career_readiness_score": career_readiness["career_readiness_score"],
            "peer_benchmark": {
                "peer_avg_readiness": career_readiness["peer_benchmark"]["peer_avg_readiness"],
                "peer_group": career_readiness["peer_benchmark"]["peer_group"],
            },
            "skill_gap_breakdown": [
                {"label": g["label"], "percentile_in_branch": g["percentile_in_branch"]}
                for g in skill_gaps
            ],
            "suggested_focus_area": {"suggestion": career_readiness["suggested_focus_area"]["suggestion"]},
            "placement_outcome_reference": {
                "placement_rate_pct": 98.5,
                "avg_salary_lpa": 18.5,
            },
        }

    # ── Step 7: Call GenAI functions via data-dict bypass ─────────────────────
    if include_genai:
        try:
            from src.genai.insights import (
                generate_atrisk_brief_from_data,
                generate_performance_summary_from_data,
                generate_career_guidance_narrative_from_data,
            )
            atrisk_brief = generate_atrisk_brief_from_data(atrisk_payload)
        except Exception as e:
            logger.warning("GenAI at-risk brief failed: %s", e)
            atrisk_brief = _fallback_atrisk_brief(atrisk_payload)

        try:
            from src.genai.insights import generate_performance_summary_from_data
            performance_summary = generate_performance_summary_from_data(perf_payload)
        except Exception as e:
            logger.warning("GenAI performance summary failed: %s", e)
            performance_summary = _fallback_performance_summary(perf_payload)

        try:
            from src.genai.insights import generate_career_guidance_narrative_from_data
            career_narrative = (
                generate_career_guidance_narrative_from_data(career_payload)
                if career_payload else None
            )
        except Exception as e:
            logger.warning("GenAI career narrative failed: %s", e)
            career_narrative = None
    else:
        atrisk_brief = _fallback_atrisk_brief(atrisk_payload)
        performance_summary = _fallback_performance_summary(perf_payload)
        career_narrative = None

    # ── Step 8: Assemble and return response ──────────────────────────────────
    return {
        "predicted_cgpa": predicted_cgpa,
        "at_risk_probability": at_risk_prob,
        "at_risk_label": at_risk_label,
        "career_readiness": career_readiness,
        "atrisk_brief": atrisk_brief,
        "performance_summary": performance_summary,
        "career_narrative": career_narrative,
        "defaulted_fields": defaulted_fields,
        "disclaimers": {
            "model1_note": (
                "CGPA prediction uses a GradientBoostingRegressor (R²=0.21). "
                "This is a directional signal only, not a reliable forecast."
            ),
            "model2_note": (
                "At-risk classification uses a RandomForestClassifier "
                "(Recall=45%, Precision=32%). ~2 in 3 flags are false alarms; "
                "over half of genuinely at-risk students may go unflagged."
            ),
            "byod_note": (
                "This assessment was run on user-supplied data, not persisted warehouse records. "
                "No data has been written to the Campus360 database."
            ),
            "career_note": (
                "Career Readiness Score is normalized against the existing Campus360 "
                "population (25,000 students). Peer benchmarks reflect that population."
            ) if career_readiness else None,
        },
        "input_echo": {k: v for k, v in full_row.items()},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Fallback Templates (used when GenAI imports fail entirely) ────────────────
def _fallback_atrisk_brief(payload: dict) -> dict:
    sid = payload["student_id"]
    branch = payload["branch"]
    tier = payload["college_tier"]
    label = payload["at_risk_label"]
    prob = payload["probability"]
    factor = payload["top_factor"]
    stu_val = payload["student_value"]
    pop_avg = payload["population_average"]
    text = (
        f"The early-warning model flagged {sid} ({branch}, Tier {tier}) as {label} "
        f"with an estimated risk probability of {prob:.1%}, primarily attributed to "
        f"{factor} ({stu_val} vs. population average of {pop_avg}). "
        f"This model has an established calibration of 45% recall and 32% precision — "
        f"meaning approximately two out of three flags are false alarms, while over half "
        f"of genuinely at-risk students remain unflagged. "
        f"Consider scheduling an informal check-in conversation to understand current workload and wellbeing."
    )
    return {
        "student_id": sid,
        "brief_text": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_probability": prob,
        "model_top_factor": factor,
        "is_fallback": True,
    }


def _fallback_performance_summary(payload: dict) -> dict:
    sid = payload["student_id"]
    pred = payload["predicted_cgpa"]
    direction = payload["direction"]
    text = (
        f"{sid}'s academic performance is projected to be {direction} "
        f"(model-predicted CGPA: {pred:.2f}/10.0). "
        f"This prediction model accounts for only ~21% of CGPA variance (R²=0.21) — "
        f"treat this as a tentative directional indicator rather than a definitive forecast."
    )
    return {
        "student_id": sid,
        "summary_text": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "predicted_cgpa": pred,
        "is_fallback": True,
    }
