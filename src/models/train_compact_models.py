"""
Train Compact Models (v2) for Campus360
=======================================
Trains and serializes the optimal 10-feature compact models for:
  - Model 1: Academic Performance Regressor (target: anchor_cgpa)
  - Model 2: Early-Warning At-Risk Classifier (target: at_risk_flag)

Evaluates on identical held-out test sets (80/20 split) with 5-fold CV.
Outputs artifacts to models/v2/:
  - models/v2/model1_performance_predictor_compact.joblib
  - models/v2/model1_performance_metrics.json
  - models/v2/model2_atrisk_classifier_compact.joblib
  - models/v2/model2_atrisk_metrics.json
  - models/v2/selected_features.json
"""

import json
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
V2_MODELS_DIR = BASE_DIR / "models" / "v2"
V2_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Feature Definitions ────────────────────────────────────────────────────────
MODEL_1_COMPACT_FEATURES = [
    "anchor_dsa_problems_solved",
    "anchor_study_hours_daily",
    "anchor_communication_skills",
    "anchor_aptitude_score",
    "effort_score",
    "screen_to_study_ratio",
    "anchor_internships_completed",
    "anchor_resume_score",
    "anchor_screen_time",
    "anchor_family_income_lpa",
]

MODEL_2_COMPACT_FEATURES = [
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


def train_model1():
    print("\n" + "=" * 80)
    print("TRAINING COMPACT MODEL 1: PERFORMANCE REGRESSOR (anchor_cgpa)")
    print("=" * 80)

    train_df = pd.read_csv(PROCESSED_DIR / "model1_performance_train.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "model1_performance_test.csv")
    target = "anchor_cgpa"

    X_train = train_df[MODEL_1_COMPACT_FEATURES]
    y_train = train_df[target]
    X_test = test_df[MODEL_1_COMPACT_FEATURES]
    y_test = test_df[target]

    print(f"Training set: {len(X_train):,} rows | Test set: {len(X_test):,} rows")
    print(f"Features ({len(MODEL_1_COMPACT_FEATURES)}): {MODEL_1_COMPACT_FEATURES}")

    # Train Gradient Boosting Regressor
    t0 = time.time()
    gbr = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        max_features="sqrt",
        min_samples_leaf=5,
        random_state=42,
    )
    gbr.fit(X_train, y_train)
    train_time = time.time() - t0

    y_pred = gbr.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(gbr, X_train, y_train, cv=kf, scoring="r2")

    print(f"\n[EVALUATION RESULTS - Model 1 Compact GBR]")
    print(f"  Test R2      : {r2:.4f} (Baseline 28-feat was 0.2096 -> Gain: +{r2 - 0.2096:+.4f})")
    print(f"  Test RMSE    : {rmse:.4f} (Baseline 28-feat was 0.7581 -> Delta: {rmse - 0.7581:+.4f})")
    print(f"  Test MAE     : {mae:.4f}")
    print(f"  5-Fold CV R2 : {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
    print(f"  Training Time: {train_time:.2f}s")

    # Serialize Model 1 GBR
    m1_path = V2_MODELS_DIR / "model1_performance_predictor_compact.joblib"
    joblib.dump(gbr, m1_path)
    print(f"Saved compact Model 1 to: {m1_path.relative_to(BASE_DIR)}")

    # Feature importances
    importances = dict(zip(MODEL_1_COMPACT_FEATURES, [round(x, 4) for x in gbr.feature_importances_]))

    metrics = {
        "model_name": "GradientBoostingRegressor (10-feature compact)",
        "target": "anchor_cgpa",
        "feature_count": len(MODEL_1_COMPACT_FEATURES),
        "features": MODEL_1_COMPACT_FEATURES,
        "feature_importances": importances,
        "test_r2": round(r2, 4),
        "test_rmse": round(rmse, 4),
        "test_mae": round(mae, 4),
        "cv_5fold_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_5fold_r2_std": round(float(cv_scores.std()), 4),
        "baseline_28feat_r2": 0.2096,
        "delta_r2_vs_baseline": round(r2 - 0.2096, 4),
        "training_time_seconds": round(train_time, 2),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(V2_MODELS_DIR / "model1_performance_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


def train_model2():
    print("\n" + "=" * 80)
    print("TRAINING COMPACT MODEL 2: AT-RISK CLASSIFIER (at_risk_flag)")
    print("=" * 80)

    train_df = pd.read_csv(PROCESSED_DIR / "model2_atrisk_train.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "model2_atrisk_test.csv")
    target = "at_risk_flag"

    X_train = train_df[MODEL_2_COMPACT_FEATURES]
    y_train = train_df[target]
    X_test = test_df[MODEL_2_COMPACT_FEATURES]
    y_test = test_df[target]

    print(f"Training set: {len(X_train):,} rows | Test set: {len(X_test):,} rows")
    print(f"Features ({len(MODEL_2_COMPACT_FEATURES)}): {MODEL_2_COMPACT_FEATURES}")
    print("Verified: Excludes anchor_backlog_history, anchor_attendance_percentage, anchor_cgpa (zero leakage).")

    # Train Logistic Regression with balanced weights
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

    print(f"\n[EVALUATION RESULTS - Model 2 Compact LogisticRegression]")
    print(f"  Recall (Class 1) : {recall:.4f} (TP: {tp:,}, FN: {fn:,})")
    print(f"  ROC-AUC          : {roc_auc:.4f} (Baseline 23-feat was 0.5190 -> Gain: +{roc_auc - 0.5190:+.4f})")
    print(f"  Precision        : {prec:.4f}")
    print(f"  F1-Score         : {f1:.4f}")
    print(f"  Accuracy         : {acc:.4f}")
    print(f"  5-Fold CV Recall : {cv_recalls.mean():.4f} +/- {cv_recalls.std():.4f}")
    print(f"  Training Time    : {train_time:.3f}s")

    # Serialize Model 2 LogReg
    m2_path = V2_MODELS_DIR / "model2_atrisk_classifier_compact.joblib"
    joblib.dump(lr, m2_path)
    print(f"Saved compact Model 2 to: {m2_path.relative_to(BASE_DIR)}")

    coefs = dict(zip(MODEL_2_COMPACT_FEATURES, [round(float(c), 4) for c in lr.coef_[0]]))

    metrics = {
        "model_name": "LogisticRegression (10-feature compact, class_weight='balanced')",
        "target": "at_risk_flag",
        "feature_count": len(MODEL_2_COMPACT_FEATURES),
        "features": MODEL_2_COMPACT_FEATURES,
        "coefficients": coefs,
        "intercept": round(float(lr.intercept_[0]), 4),
        "test_recall": round(recall, 4),
        "test_roc_auc": round(roc_auc, 4),
        "test_precision": round(prec, 4),
        "test_f1": round(f1, 4),
        "test_accuracy": round(acc, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "cv_5fold_recall_mean": round(float(cv_recalls.mean()), 4),
        "cv_5fold_recall_std": round(float(cv_recalls.std()), 4),
        "training_time_seconds": round(train_time, 3),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(V2_MODELS_DIR / "model2_atrisk_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


def save_selected_features():
    schema = {
        "version": "v2_compact",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model1_performance": {
            "target": "anchor_cgpa",
            "target_range": [5.0, 10.0],
            "algorithm": "GradientBoostingRegressor",
            "feature_count": len(MODEL_1_COMPACT_FEATURES),
            "features": MODEL_1_COMPACT_FEATURES,
            "engineered_features": ["effort_score", "screen_to_study_ratio"],
            "raw_input_fields": [f for f in MODEL_1_COMPACT_FEATURES if f not in ["effort_score", "screen_to_study_ratio"]],
        },
        "model2_atrisk": {
            "target": "at_risk_flag",
            "target_classes": [0, 1],
            "algorithm": "LogisticRegression(class_weight='balanced')",
            "feature_count": len(MODEL_2_COMPACT_FEATURES),
            "features": MODEL_2_COMPACT_FEATURES,
            "engineered_features": ["wellness_score", "screen_to_study_ratio"],
            "raw_input_fields": [f for f in MODEL_2_COMPACT_FEATURES if f not in ["wellness_score", "screen_to_study_ratio"]],
            "excluded_leakage_fields": ["anchor_backlog_history", "anchor_attendance_percentage", "anchor_cgpa"],
        },
    }
    schema_path = V2_MODELS_DIR / "selected_features.json"
    with open(schema_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Saved feature schemas to: {schema_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    m1_metrics = train_model1()
    m2_metrics = train_model2()
    save_selected_features()
    print("\n" + "=" * 80)
    print("ALL COMPACT V2 MODELS SUCCESSFULLY TRAINED AND SERIALIZED!")
    print("=" * 80 + "\n")
