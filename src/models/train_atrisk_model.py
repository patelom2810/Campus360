"""
Train Model 2 — At-Risk Student Classifier
Sole Production Model: 10-Feature Compact LogisticRegression (class_weight='balanced')

Target:  at_risk_flag (engineered composite label)
Features (10):
  - anchor_gym_frequency
  - anchor_self_learning_hours
  - anchor_gaming_hours
  - anchor_development_projects_count
  - anchor_sleep_hours
  - wellness_score
  - screen_to_study_ratio
  - anchor_communication_skills
  - anchor_study_hours_daily
  - anchor_screen_time

EXCLUDES: anchor_backlog_history, anchor_attendance_percentage, anchor_cgpa (zero leakage).
Decision Threshold: 0.50.

Output:
  - models/model2_atrisk_classifier.joblib
  - models/model2_atrisk_metrics.json
"""

import json
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "at_risk_flag"

MODEL_2_FEATURES = [
    "anchor_gym_frequency",
    "anchor_self_learning_hours",
    "anchor_gaming_hours",
    "anchor_development_projects_count",
    "anchor_sleep_hours",
    "wellness_score",
    "screen_to_study_ratio",
    "anchor_communication_skills",
    "anchor_study_hours_daily",
    "anchor_screen_time",
]

# Anti-leakage quarantine list
LEAKAGE_COLUMNS = [
    "anchor_backlog_history",
    "anchor_attendance_percentage",
    "anchor_cgpa",
]


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


def train():
    print("=" * 80)
    print("TRAINING SOLE PRODUCTION MODEL 2: 10-FEATURE COMPACT CLASSIFIER (at_risk_flag)")
    print("=" * 80)

    for col in LEAKAGE_COLUMNS:
        assert col not in MODEL_2_FEATURES, f"CRITICAL: Leakage column {col} found in MODEL_2_FEATURES!"

    train_path = PROCESSED_DIR / "model2_atrisk_train.csv"
    test_path = PROCESSED_DIR / "model2_atrisk_test.csv"

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    train_df = add_engineered_features(train_df)
    test_df = add_engineered_features(test_df)

    X_train = train_df[MODEL_2_FEATURES]
    y_train = train_df[TARGET]
    X_test = test_df[MODEL_2_FEATURES]
    y_test = test_df[TARGET]

    print(f"Training set: {len(X_train):,} rows | Test set: {len(X_test):,} rows")
    print(f"Features ({len(MODEL_2_FEATURES)}): {MODEL_2_FEATURES}")
    print("Verified: Excludes anchor_backlog_history, anchor_attendance_percentage, anchor_cgpa (zero leakage).")

    t0 = time.time()
    lr = LogisticRegression(
        C=1.0,
        penalty="l2",
        solver="liblinear",
        class_weight="balanced",
        random_state=42,
    )
    lr.fit(X_train, y_train)
    train_time = time.time() - t0

    y_prob = lr.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.50).astype(int)

    recall = recall_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)
    prec = precision_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    acc = accuracy_score(y_test, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_recalls = cross_val_score(lr, X_train, y_train, cv=skf, scoring="recall")

    print("\n[EVALUATION RESULTS - Model 2 Compact LogisticRegression]")
    print(f"  Recall (Class 1) : {recall:.4f} (TP: {tp:,}, FN: {fn:,})")
    print(f"  ROC-AUC          : {roc_auc:.4f}")
    print(f"  Precision        : {prec:.4f}")
    print(f"  F1-Score         : {f1:.4f}")
    print(f"  Accuracy         : {acc:.4f}")
    print(f"  5-Fold CV Recall : {cv_recalls.mean():.4f} +/- {cv_recalls.std():.4f}")
    print(f"  Training Time    : {train_time:.3f}s")

    # Serialize
    m2_path = MODELS_DIR / "model2_atrisk_classifier.joblib"
    joblib.dump(lr, m2_path)
    print(f"Saved production Model 2 to: {m2_path.relative_to(BASE_DIR)}")

    coefs = dict(zip(MODEL_2_FEATURES, [round(float(c), 4) for c in lr.coef_[0]]))
    importances = {k: round(abs(float(v)), 4) for k, v in coefs.items()}

    metrics = {
        "model_name": "LogisticRegression (10-feature compact, class_weight='balanced')",
        "target": TARGET,
        "feature_count": len(MODEL_2_FEATURES),
        "features": MODEL_2_FEATURES,
        "coefficients": coefs,
        "feature_importances": importances,
        "disclosure_text": "Lifestyle and behavioral data alone provides early warning screening (recall 0.50), not diagnostic certainty.",
        "intercept": round(float(lr.intercept_[0]), 4),
        "test_recall": round(float(recall), 4),
        "test_roc_auc": round(float(roc_auc), 4),
        "test_precision": round(float(prec), 4),
        "test_f1": round(float(f1), 4),
        "test_accuracy": round(float(acc), 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "cv_5fold_recall_mean": round(float(cv_recalls.mean()), 4),
        "cv_5fold_recall_std": round(float(cv_recalls.std()), 4),
        "training_time_seconds": round(float(train_time), 3),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    metrics_path = MODELS_DIR / "model2_atrisk_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved production Model 2 metrics to: {metrics_path.relative_to(BASE_DIR)}")

    return lr, metrics


if __name__ == "__main__":
    train()
