"""
Train Model 2 — At-Risk Student Classifier (Deployed Version)

Target:  at_risk_flag (engineered composite label)
Features: 23 features total:
          - 11 original anchor lifestyle features
          - 10 new non-leakage anchor features
          - 2 engineered interaction features (wellness_score, screen_to_study_ratio)
          EXCLUDES anchor_backlog_history, anchor_attendance_percentage,
          anchor_cgpa to prevent label leakage.
Algorithm: RandomForestClassifier (RandomizedSearchCV: 30 iterations, 5-fold CV,
           optimising F1 score to avoid degenerate all-positive solutions).
Decision Threshold: Locked to default 0.50.
Output:
  - models/model2_atrisk_classifier.joblib
  - models/model2_atrisk_metrics.json
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
from sklearn.model_selection import RandomizedSearchCV

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

TARGET = "at_risk_flag"

# ── Feature Definitions & Leakage Guards ───────────────────────────────
ORIGINAL_FEATURES = [
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
]

NEW_ANCHOR_FEATURES = [
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
]

ENGINEERED_FEATURES = [
    "wellness_score",
    "screen_to_study_ratio",
]

ALL_FEATURES = ORIGINAL_FEATURES + NEW_ANCHOR_FEATURES + ENGINEERED_FEATURES
PREV_TEST_RECALL = 0.3486

# Columns that MUST NOT appear in features (label leakage)
LEAKED_COLUMNS = {"anchor_backlog_history", "anchor_attendance_percentage", "anchor_cgpa"}


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


def evaluate_model(model, X_test, y_test, threshold=0.50):
    """Compute all evaluation metrics at the specified threshold."""
    y_probs = model.predict_proba(X_test)[:, 1]
    y_pred = (y_probs >= threshold).astype(int)

    roc_auc = float(roc_auc_score(y_test, y_probs))
    accuracy = float(accuracy_score(y_test, y_pred))
    precision_1 = float(precision_score(y_test, y_pred, pos_label=1, zero_division=0))
    recall_1 = float(recall_score(y_test, y_pred, pos_label=1, zero_division=0))
    f1_1 = float(f1_score(y_test, y_pred, pos_label=1, zero_division=0))
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(y_test, y_pred, target_names=["Safe (0)", "At-Risk (1)"])

    return {
        "roc_auc": roc_auc,
        "accuracy": accuracy,
        "precision_1": precision_1,
        "recall_1": recall_1,
        "f1_1": f1_1,
        "confusion_matrix": cm,
        "classification_report": report,
    }


def is_degenerate(metrics):
    """Check if model prediction is near-degenerate."""
    cm = metrics["confusion_matrix"]
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]

    # Check 1: Any cell in confusion matrix < 20
    if tn < 20 or fp < 20 or fn < 20 or tp < 20:
        return True, f"Confusion matrix has a cell with < 20 samples: {cm}"

    # Check 2: Recall > 0.90 AND Precision < 0.35 simultaneously
    if metrics["recall_1"] > 0.90 and metrics["precision_1"] < 0.35:
        return True, f"Recall is {metrics['recall_1']:.4f} (>0.9) while precision is {metrics['precision_1']:.4f} (<0.35) — over-prediction detected"

    return False, "Non-degenerate"


def train():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("MODEL 2: AT-RISK CLASSIFIER (CORRECTED DEPLOYED TRAINING)")
    print("=" * 72)

    # ── Leakage guard check ─────────────────────────────────────────────
    overlap = set(ALL_FEATURES) & LEAKED_COLUMNS
    if overlap:
        raise ValueError(f"LEAKAGE DETECTED: features contain label-defining columns: {overlap}")
    print("Leakage check PASSED: zero label-defining columns present.")

    # ── Load data ───────────────────────────────────────────────────────
    train_df = pd.read_csv(PROCESSED_DIR / "model2_atrisk_train.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "model2_atrisk_test.csv")

    train_df = add_engineered_features(train_df)
    test_df = add_engineered_features(test_df)

    X_train, y_train = train_df[ALL_FEATURES], train_df[TARGET]
    X_test, y_test = test_df[ALL_FEATURES], test_df[TARGET]

    print(f"\nFeature Space ({len(ALL_FEATURES)} features):")
    for i, f in enumerate(ALL_FEATURES, 1):
        print(f"  {i:>2d}. {f}")

    print(f"\nTraining data : {X_train.shape[0]:,} rows x {X_train.shape[1]} features")
    print(f"Test data     : {X_test.shape[0]:,} rows x {X_test.shape[1]} features")
    print(f"Train balance : {dict(y_train.value_counts())}")
    print(f"Test balance  : {dict(y_test.value_counts())}\n")

    # ── Hyperparameter Search (Scoring: F1, no extreme class_weight) ─────
    print("-" * 72)
    print("STEP 2: Hyperparameter search (RandomizedSearchCV: 30 iter, 5-fold CV, scoring='f1')...")
    print("-" * 72)

    param_distributions = {
        "n_estimators": [200, 400, 600],
        "max_depth": [6, 10, 14, None],
        "min_samples_leaf": [1, 3, 5, 10],
        "max_features": ["sqrt", "log2"],
        "class_weight": ["balanced", {0: 1, 1: 1.5}, {0: 1, 1: 2}],
    }

    base_model = RandomForestClassifier(random_state=42, n_jobs=-1)
    search = RandomizedSearchCV(
        base_model,
        param_distributions,
        n_iter=30,
        cv=5,
        scoring="f1",
        random_state=42,
        n_jobs=1,
        verbose=1,
    )
    search.fit(X_train, y_train)

    best_model = search.best_estimator_
    best_params = search.best_params_
    print(f"\nBest search params: {best_params}")
    print(f"Best CV F1: {search.best_score_:.4f}")

    # ── Evaluate on held-out test set at default 0.50 threshold ─────────
    metrics = evaluate_model(best_model, X_test, y_test, threshold=0.50)

    # ── STEP 4: Sanity check before saving ──────────────────────────────
    print("\n" + "-" * 72)
    print("STEP 4: Sanity check on candidate model...")
    print("-" * 72)
    is_bad, reason = is_degenerate(metrics)
    if is_bad:
        print(f"  [REJECTED] candidate model: {reason}")
        print("  → Falling back to default class_weight='balanced' with baseline parameters...")
        fallback_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        fallback_model.fit(X_train, y_train)
        best_model = fallback_model
        best_params = {"n_estimators": 200, "max_depth": 8, "class_weight": "balanced"}
        metrics = evaluate_model(best_model, X_test, y_test, threshold=0.50)
        print("  Fallback model trained successfully.")
    else:
        print("  [PASSED] Candidate model PASSED all sanity checks (non-degenerate).")

    # ── Print Metrics & STEP 3: Report ROC AUC Explicitly ───────────────
    print("\n" + "=" * 72)
    print("STEP 3 & 5: TEST SET EVALUATION AT DEFAULT THRESHOLD 0.50")
    print("=" * 72)
    print(f"  ROC AUC    : {metrics['roc_auc']:.4f}")
    if 0.50 <= metrics["roc_auc"] <= 0.55:
        print("    → Note: ROC AUC is between 0.50 and 0.55. The feature set has little to no")
        print("      real discriminative power; any classification separation is marginal.")
    print(f"  Accuracy   : {metrics['accuracy']:.4f}")
    print(f"  Precision  : {metrics['precision_1']:.4f}  (class 1)")
    print(f"  Recall     : {metrics['recall_1']:.4f}  (class 1)")
    print(f"  F1-Score   : {metrics['f1_1']:.4f}  (class 1)")
    cm = metrics["confusion_matrix"]
    print(f"\nConfusion Matrix:")
    print(f"  [[TN={cm[0][0]:>5d}  FP={cm[0][1]:>5d}]")
    print(f"   [FN={cm[1][0]:>5d}  TP={cm[1][1]:>5d}]]")
    print(f"\nClassification Report:\n{metrics['classification_report']}")

    # ── Feature importances ─────────────────────────────────────────────
    importances = dict(zip(ALL_FEATURES, best_model.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print(f"Top 5 Features by Importance:")
    for feat, imp in sorted_imp[:5]:
        print(f"  {feat:40s} {imp:.4f}")

    # ── Save Deployed Artifacts ─────────────────────────────────────────
    model_path = MODELS_DIR / "model2_atrisk_classifier.joblib"
    joblib.dump(best_model, model_path)
    print(f"\nSaved model  → {model_path.relative_to(BASE_DIR)}")

    # Clean best params for JSON serialization
    best_params_clean = {}
    for k, v in best_params.items():
        if isinstance(v, dict):
            best_params_clean[k] = {str(dk): dv for dk, dv in v.items()}
        elif isinstance(v, (np.integer, int)):
            best_params_clean[k] = int(v)
        else:
            best_params_clean[k] = v

    saved_metrics = {
        "model": "RandomForestClassifier",
        "target": TARGET,
        "features": ALL_FEATURES,
        "feature_count": len(ALL_FEATURES),
        "original_feature_count": len(ORIGINAL_FEATURES),
        "added_anchor_feature_count": len(NEW_ANCHOR_FEATURES),
        "engineered_feature_count": len(ENGINEERED_FEATURES),
        "leaked_columns_excluded": sorted(LEAKED_COLUMNS),
        "best_params": best_params_clean,
        "decision_threshold": 0.50,
        "roc_auc": round(metrics["roc_auc"], 4),
        "test_accuracy": round(metrics["accuracy"], 4),
        "test_precision_class1": round(metrics["precision_1"], 4),
        "test_recall_class1": round(metrics["recall_1"], 4),
        "test_f1_class1": round(metrics["f1_1"], 4),
        "confusion_matrix": metrics["confusion_matrix"],
        "classification_report": metrics["classification_report"],
        "previous_test_recall_class1": PREV_TEST_RECALL,
        "feature_importances": {k: round(v, 4) for k, v in sorted_imp},
        "train_rows": len(X_train),
        "test_rows": len(X_test),
    }

    metrics_path = MODELS_DIR / "model2_atrisk_metrics.json"
    metrics_path.write_text(json.dumps(saved_metrics, indent=2))
    print(f"Saved metrics → {metrics_path.relative_to(BASE_DIR)}")

    return best_model, saved_metrics


if __name__ == "__main__":
    train()
