"""
Label Integrity Sanity Check — At-Risk Classification Label Reconstruction Check

PURPOSE:
  ENGINEERING VALIDATION ONLY — NOT DEPLOYED.
  A model trained with anchor_backlog_history, anchor_attendance_percentage,
  and anchor_cgpa included as features achieves near-perfect separation
  (ROC AUC ≈ 1.0) when predicting at_risk_flag. This is EXPECTED and NOT a
  predictive finding — at_risk_flag is deterministically defined as a
  threshold function of these exact three columns (see label engineering),
  so this result only confirms the label was constructed correctly, i.e. it
  recovers from its own defining formula. It is reported here as an engineering
  validation step, not as evidence that academic features 'predict' risk in
  any generalizable sense.

Outputs:
  - models/label_reconstruction_sanity_check.joblib (primary)
  - models/label_reconstruction_sanity_check.json (primary)
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

TARGET = "at_risk_flag"

# 23 lifestyle/skill features from deployed Model 2
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

# Intentionally added academic columns for diagnostic benchmark
ACADEMIC_DIAGNOSTIC_FEATURES = [
    "anchor_backlog_history",
    "anchor_attendance_percentage",
    "anchor_cgpa",
]

DIAGNOSTIC_FEATURES = LIFESTYLE_SKILL_FEATURES + ACADEMIC_DIAGNOSTIC_FEATURES


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure engineered interaction features exist on the dataframe."""
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


def train_diagnostic():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("LABEL INTEGRITY SANITY CHECK: AT-RISK CLASSIFICATION (FORMULA RECONSTRUCTION)")
    print("PURPOSE: ENGINEERING VALIDATION ONLY — NOT DEPLOYED")
    print("=" * 76)

    # Load master dataset and reconstruct identical stratified split
    master_file = PROCESSED_DIR / "student_master_wide.csv"
    if not master_file.exists():
        raise FileNotFoundError(f"Master file not found: {master_file}")

    df = pd.read_csv(master_file)
    df = add_engineered_features(df)

    # Identical stratified split matching Model 2
    train_df, test_df = train_test_split(
        df, test_size=0.20, random_state=42, shuffle=True, stratify=df[TARGET]
    )

    X_train = train_df[DIAGNOSTIC_FEATURES]
    y_train = train_df[TARGET]
    X_test = test_df[DIAGNOSTIC_FEATURES]
    y_test = test_df[TARGET]

    print(f"\nFeature Space ({len(DIAGNOSTIC_FEATURES)} features):")
    print(f"  Lifestyle & skill features : {len(LIFESTYLE_SKILL_FEATURES)}")
    print(f"  Academic formula features  : {len(ACADEMIC_DIAGNOSTIC_FEATURES)} {ACADEMIC_DIAGNOSTIC_FEATURES}")
    print(f"  Train set: {len(X_train):,} rows | Test set: {len(X_test):,} rows\n")

    # Train Random Forest Classifier with balanced weights
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate on held-out test set
    y_probs = model.predict_proba(X_test)[:, 1]
    y_pred = (y_probs >= 0.50).astype(int)

    diag_roc_auc = float(roc_auc_score(y_test, y_probs))
    diag_accuracy = float(accuracy_score(y_test, y_pred))
    diag_precision = float(precision_score(y_test, y_pred, pos_label=1, zero_division=0))
    diag_recall = float(recall_score(y_test, y_pred, pos_label=1, zero_division=0))
    diag_f1 = float(f1_score(y_test, y_pred, pos_label=1, zero_division=0))
    diag_cm = confusion_matrix(y_test, y_pred).tolist()
    diag_report = classification_report(y_test, y_pred, target_names=["Safe (0)", "At-Risk (1)"])

    print("── Label Integrity Sanity Check Performance ──")
    print(f"  ROC AUC   : {diag_roc_auc:.4f}")
    print(f"  Recall    : {diag_recall:.4f}")
    print(f"  Precision : {diag_precision:.4f}")
    print(f"  Accuracy  : {diag_accuracy:.4f}")
    print(f"  F1-Score  : {diag_f1:.4f}")
    print(f"\nConfusion Matrix:")
    print(f"  [[TN={diag_cm[0][0]:>5d}  FP={diag_cm[0][1]:>5d}]")
    print(f"   [FN={diag_cm[1][0]:>5d}  TP={diag_cm[1][1]:>5d}]]")

    # Top features
    importances = dict(zip(DIAGNOSTIC_FEATURES, model.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print(f"\nTop 5 Features by Importance:")
    for feat, imp in sorted_imp[:5]:
        print(f"  {feat:40s} {imp:.4f}")

    print("\n" + "=" * 76)
    print("LABEL RECONSTRUCTION SANITY CHECK")
    print("Note: This is a circularity check confirming recovery from the defining formula,")
    print("NOT a comparison of predictive power.")
    print("=" * 76)
    print(f"{'Metric':<22s} | {'Label Reconstruction Check (Academic + Lifestyle)':<50s}")
    print("-" * 76)
    print(f"{'ROC AUC':<22s} | {diag_roc_auc:<50.4f}")
    print(f"{'Recall (Class 1)':<22s} | {diag_recall:<50.4f}")
    print(f"{'Precision (Class 1)':<22s} | {diag_precision:<50.4f}")
    print(f"{'Accuracy':<22s} | {diag_accuracy:<50.4f}")
    print("-" * 76)

    # Save Artifacts
    primary_model_path = MODELS_DIR / "label_reconstruction_sanity_check.joblib"
    joblib.dump(model, primary_model_path)
    print(f"\nSaved model → {primary_model_path.relative_to(BASE_DIR)}")

    sanity_metrics = {
        "purpose": (
            "Label Integrity Sanity Check: A model trained with anchor_backlog_history, "
            "anchor_attendance_percentage, and anchor_cgpa included as features achieves "
            "near-perfect separation (ROC AUC ≈ 1.0) when predicting at_risk_flag. This is "
            "EXPECTED and NOT a predictive finding — at_risk_flag is deterministically defined "
            "as a threshold function of these exact three columns (see label_engineering section "
            "above), so this result only confirms the label was constructed correctly, i.e. it "
            "recovers from its own defining formula. It is reported here as an engineering validation "
            "step, not as evidence that academic features 'predict' risk in any generalizable sense."
        ),
        "model": "RandomForestClassifier",
        "target": TARGET,
        "features": DIAGNOSTIC_FEATURES,
        "feature_count": len(DIAGNOSTIC_FEATURES),
        "academic_features_included": ACADEMIC_DIAGNOSTIC_FEATURES,
        "lifestyle_skill_features_count": len(LIFESTYLE_SKILL_FEATURES),
        "decision_threshold": 0.50,
        "roc_auc": round(diag_roc_auc, 4),
        "test_accuracy": round(diag_accuracy, 4),
        "test_precision_class1": round(diag_precision, 4),
        "test_recall_class1": round(diag_recall, 4),
        "test_f1_class1": round(diag_f1, 4),
        "confusion_matrix": diag_cm,
        "classification_report": diag_report,
        "feature_importances": {k: round(v, 4) for k, v in sorted_imp},
        "train_rows": len(X_train),
        "test_rows": len(X_test),
    }

    primary_metrics_path = MODELS_DIR / "label_reconstruction_sanity_check.json"
    primary_metrics_path.write_text(json.dumps(sanity_metrics, indent=2))
    print(f"Saved sanity check metrics → {primary_metrics_path.relative_to(BASE_DIR)}")

    return model, sanity_metrics


if __name__ == "__main__":
    train_diagnostic()
