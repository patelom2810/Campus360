"""
Non-Circular Ceiling Test: Lifestyle-Only vs Lifestyle + Academic Features

PURPOSE:
  Evaluates whether academic context (backlogs, attendance, CGPA) adds predictive
  power beyond lifestyle/skills features when predicting an INDEPENDENT risk proxy
  (suvidya_pass_fail, mapped to 1=Fail, 0=Pass).

  Unlike at_risk_flag (which is deterministically derived from backlogs, attendance,
  and CGPA), suvidya_pass_fail comes from an independent external data source
  (Suvidya performance records) with ZERO definitional overlap with any input feature.
  Therefore, any observed performance gap is a legitimate predictive comparison.

Scope:
  Evaluated strictly on the ~5,000 students where has_suvidya_match == 1.
  NOT wired into the deployed dashboard/API — for presentation and methodological validation only.

Outputs:
  - models/suvidya_ceiling_test_lifestyle_only.joblib
  - models/suvidya_ceiling_test_with_academic.joblib
  - models/suvidya_ceiling_test_comparison.json
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

# 23 lifestyle and skills features (identical to deployed Model 2)
LIFESTYLE_SKILL_FEATURES = [
    "anchor_sleep_hours",
    "anchor_screen_time",
    "anchor_gaming_hours",
    "anchor_stress_level",
    "anchor_burnout_score",
    "anchor_study_hours_daily",
    "anchor_self_learning_hours",
    "anchor_motivation_level",
    "anchor_adaptability_score",
    "anchor_gym_frequency",
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
    "wellness_score",
    "screen_to_study_ratio",
]

# 3 academic telemetry features
ACADEMIC_FEATURES = [
    "anchor_backlog_history",
    "anchor_attendance_percentage",
    "anchor_cgpa",
]

COMBINED_FEATURES = LIFESTYLE_SKILL_FEATURES + ACADEMIC_FEATURES


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "screen_to_study_ratio" not in df.columns:
        df["screen_to_study_ratio"] = df["anchor_screen_time"] / (df["anchor_study_hours_daily"] + 1)
    if "wellness_score" not in df.columns:
        df["wellness_score"] = (
            df["anchor_sleep_hours"]
            - (df["anchor_stress_level"] / 10.0)
            - (df["anchor_burnout_score"] / 10.0)
        )
    return df


def train_and_evaluate(X_train, y_train, X_test, y_test, feature_names, model_name):
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    y_probs = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_probs >= 0.50).astype(int)

    metrics = {
        "model_name": model_name,
        "feature_count": len(feature_names),
        "features": feature_names,
        "roc_auc": round(float(roc_auc_score(y_test, y_probs)), 4),
        "recall_class1": round(float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        "precision_class1": round(float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "f1_class1": round(float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(
            y_test, y_pred, target_names=["Pass (0)", "Fail (1)"], zero_division=0
        ),
    }

    importances = dict(zip(feature_names, clf.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    metrics["top_5_features"] = {k: round(v, 4) for k, v in sorted_imp[:5]}

    return clf, metrics


def run_ceiling_test():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("GENUINE NON-CIRCULAR CEILING TEST: SUVIDYA PASS/FAIL RISK PROXY")
    print("Independent Target: suvidya_pass_fail (1=Fail, 0=Pass)")
    print("Evaluated strictly on Suvidya-matched subset (has_suvidya_match == 1)")
    print("=" * 80)

    master_file = PROCESSED_DIR / "student_master_wide.csv"
    if not master_file.exists():
        raise FileNotFoundError(f"Master file not found: {master_file}")

    df = pd.read_csv(master_file)
    df = add_engineered_features(df)

    # Filter to Suvidya-matched subset
    suvidya_subset = df[df["has_suvidya_match"] == 1].copy()
    sample_size = len(suvidya_subset)
    print(f"\nTotal students in master dataset : {len(df):,}")
    print(f"Suvidya-matched cohort size      : {sample_size:,} (only rows with this ground-truth target)")

    # Target encoding: 1 = Fail, 0 = Pass
    target_clean = suvidya_subset["suvidya_pass_fail"].astype(str).str.strip().str.lower()
    suvidya_subset["target"] = (target_clean == "fail").astype(int)

    class_counts = suvidya_subset["target"].value_counts()
    fail_count = class_counts.get(1, 0)
    pass_count = class_counts.get(0, 0)
    print(f"Target distribution:\n  Pass (0): {pass_count:,} ({pass_count/sample_size*100:.2f}%)")
    print(f"  Fail (1): {fail_count:,} ({fail_count/sample_size*100:.2f}%)\n")

    # 80/20 Stratified Split — EXACT SAME ROWS for both models
    train_df, test_df = train_test_split(
        suvidya_subset,
        test_size=0.20,
        random_state=42,
        shuffle=True,
        stratify=suvidya_subset["target"],
    )

    y_train = train_df["target"]
    y_test = test_df["target"]
    print(f"Stratified Split: {len(train_df):,} train rows | {len(test_df):,} test rows")
    print(f"Test Set Class 1 (Fail) count: {y_test.sum():,} / {len(y_test):,}")

    # Model A: Lifestyle & Skills Only (23 features)
    print("\n" + "-" * 60)
    print("Training Model A: Lifestyle & Skills Only (23 features)...")
    X_train_A = train_df[LIFESTYLE_SKILL_FEATURES]
    X_test_A = test_df[LIFESTYLE_SKILL_FEATURES]
    model_A, metrics_A = train_and_evaluate(
        X_train_A, y_train, X_test_A, y_test, LIFESTYLE_SKILL_FEATURES, "Lifestyle Only"
    )

    # Model B: Lifestyle + Academic Telemetry (26 features)
    print("Training Model B: Lifestyle + Academic Telemetry (26 features)...")
    X_train_B = train_df[COMBINED_FEATURES]
    X_test_B = test_df[COMBINED_FEATURES]
    model_B, metrics_B = train_and_evaluate(
        X_train_B, y_train, X_test_B, y_test, COMBINED_FEATURES, "Lifestyle + Academic"
    )

    # Print Side-by-Side Comparison
    print("\n" + "=" * 80)
    print("NON-CIRCULAR CEILING TEST COMPARISON TABLE (Target = suvidya_pass_fail)")
    print("=" * 80)
    print(f"{'Metric':<24s} | {'Model A (Lifestyle Only)':<24s} | {'Model B (Lifestyle + Academic)':<30s}")
    print("-" * 84)
    print(f"{'ROC AUC':<24s} | {metrics_A['roc_auc']:<24.4f} | {metrics_B['roc_auc']:<30.4f}")
    print(f"{'Recall (Class 1 / Fail)':<24s} | {metrics_A['recall_class1']:<24.4f} | {metrics_B['recall_class1']:<30.4f}")
    print(f"{'Precision (Class 1 / Fail)':<24s} | {metrics_A['precision_class1']:<24.4f} | {metrics_B['precision_class1']:<30.4f}")
    print(f"{'Accuracy':<24s} | {metrics_A['accuracy']:<24.4f} | {metrics_B['accuracy']:<30.4f}")
    print(f"{'F1-Score (Class 1)':<24s} | {metrics_A['f1_class1']:<24.4f} | {metrics_B['f1_class1']:<30.4f}")
    print("-" * 84)
    print(f"Confusion Matrix A (Lifestyle):\n  {metrics_A['confusion_matrix']}")
    print(f"Confusion Matrix B (Lifestyle + Academic):\n  {metrics_B['confusion_matrix']}")

    print("\nTop 5 Features — Model A (Lifestyle Only):")
    for feat, imp in metrics_A["top_5_features"].items():
        print(f"  {feat:35s} : {imp:.4f}")

    print("\nTop 5 Features — Model B (Lifestyle + Academic):")
    for feat, imp in metrics_B["top_5_features"].items():
        print(f"  {feat:35s} : {imp:.4f}")

    # Honest Synthesis Note
    auc_diff = metrics_B["roc_auc"] - metrics_A["roc_auc"]
    print("\n" + "-" * 80)
    print("ANALYSIS OF RESULTS:")
    if abs(metrics_A["roc_auc"] - 0.5) < 0.05 and abs(metrics_B["roc_auc"] - 0.5) < 0.05:
        finding = (
            f"Both models demonstrate near-random discriminative power on this target "
            f"(AUC A={metrics_A['roc_auc']:.4f}, AUC B={metrics_B['roc_auc']:.4f}, Δ={auc_diff:+.4f}). "
            f"Given the small sample size (~5,000 rows, 265 Fail cases) and the independent nature "
            f"of the Suvidya external grading schema, neither lifestyle nor anchor academic telemetry "
            f"cleanly separates pass/fail outcomes on this subset."
        )
    elif auc_diff > 0.05:
        finding = (
            f"Model B outperforms Model A (AUC A={metrics_A['roc_auc']:.4f}, AUC B={metrics_B['roc_auc']:.4f}, "
            f"Δ={auc_diff:+.4f}). Because suvidya_pass_fail was not constructed from any of these features, "
            f"this reflects genuine non-circular predictive contribution from academic telemetry."
        )
    else:
        finding = (
            f"Model A achieved AUC={metrics_A['roc_auc']:.4f} vs Model B AUC={metrics_B['roc_auc']:.4f} "
            f"(Δ={auc_diff:+.4f}). The marginal difference indicates that academic features provide "
            f"negligible additional separation for this specific external target."
        )
    print(finding)
    print("-" * 80)

    # Save artifacts
    model_a_path = MODELS_DIR / "suvidya_ceiling_test_lifestyle_only.joblib"
    model_b_path = MODELS_DIR / "suvidya_ceiling_test_with_academic.joblib"
    comparison_path = MODELS_DIR / "suvidya_ceiling_test_comparison.json"

    joblib.dump(model_A, model_a_path)
    joblib.dump(model_B, model_b_path)
    print(f"\nSaved Model A artifact → {model_a_path.relative_to(BASE_DIR)}")
    print(f"Saved Model B artifact → {model_b_path.relative_to(BASE_DIR)}")

    comparison_payload = {
        "purpose": (
            "Genuine non-circular comparison of lifestyle-only vs lifestyle+academic features "
            "predicting an independent risk proxy (suvidya_pass_fail, 1=Fail, 0=Pass). "
            "Evaluated strictly on the Suvidya-matched subcohort."
        ),
        "sample_size": sample_size,
        "sample_source": "Suvidya-matched subset (has_suvidya_match == 1)",
        "target_variable": "suvidya_pass_fail (1=Fail, 0=Pass)",
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "test_fail_cases": int(y_test.sum()),
        "test_pass_cases": int(len(test_df) - y_test.sum()),
        "decision_threshold": 0.50,
        "honest_finding_summary": finding,
        "model_a_lifestyle_only": metrics_A,
        "model_b_lifestyle_plus_academic": metrics_B,
        "roc_auc_gap": round(auc_diff, 4),
    }

    comparison_path.write_text(json.dumps(comparison_payload, indent=2))
    print(f"Saved comparison JSON  → {comparison_path.relative_to(BASE_DIR)}")

    return metrics_A, metrics_B


if __name__ == "__main__":
    run_ceiling_test()
