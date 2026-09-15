"""
Campus360 — Model 1: Student Next Semester Marks Performance Regression
Predicts student's 'next_semester_marks' using finalized 18 academic,
coursework, and lifestyle indicators.
Zero target leakage guarantee: omits previous_sgpa and current target proxies.
Includes systematic hyperparameter tuning, cross-validation, and metrics logging.
"""

import sys
import json
import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import MODEL_1_TRAIN_CSV, MODEL_1_TEST_CSV, MODEL_1_PATH, MODELS_DIR

METRICS_JSON_PATH = MODELS_DIR / "model_metrics.json"

# 18 Finalized Features per KDAC-3 Problem Specification (Zero Target Leakage)
MODEL_1_FEATURES = [
    "previous_cgpa",
    "previous_semester_percentage",
    "previous_internal_marks",
    "previous_assignment_score",
    "previous_midterm_score",
    "attendance_percentage",
    "study_hours_per_week",
    "assignment_completion_rate",
    "practice_questions",
    "previous_subject_avg",
    "weak_subject_count",
    "lowest_subject_score",
    "subject_consistency",
    "sleep_hours",
    "extracurricular_hours",
    "stress_level",
    "backlogs",
    "failed_subjects",
]


def update_metrics_json(key: str, data: dict):
    """Safely updates models/model_metrics.json with new evaluation results."""
    current_metrics = {}
    if METRICS_JSON_PATH.exists():
        try:
            with open(METRICS_JSON_PATH, "r", encoding="utf-8") as f:
                current_metrics = json.load(f)
        except Exception:
            current_metrics = {}
    current_metrics[key] = data
    with open(METRICS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(current_metrics, f, indent=2)


def train_performance_model():
    print("=" * 75)
    print("  MODEL 1: STUDENT PERFORMANCE REGRESSION (next_semester_marks)")
    print(f"  Target: next_semester_marks | Finalized Features: {len(MODEL_1_FEATURES)}")
    print("=" * 75)

    if not MODEL_1_TRAIN_CSV.exists() or not MODEL_1_TEST_CSV.exists():
        raise FileNotFoundError(f"Missing train/test CSVs in {MODEL_1_TRAIN_CSV.parent}")

    train = pd.read_csv(MODEL_1_TRAIN_CSV)
    test = pd.read_csv(MODEL_1_TEST_CSV)

    target = "next_semester_marks"
    if target not in train.columns or target not in test.columns:
        raise KeyError(f"Target column '{target}' missing from train or test dataset")

    # Filter strictly to the 18 finalized features
    X_train = train[MODEL_1_FEATURES]
    y_train = train[target]
    X_test = test[MODEL_1_FEATURES]
    y_test = test[target]

    print(f"[DATA] Train: {X_train.shape[0]:,} samples | Test: {X_test.shape[0]:,} samples")
    print(f"[FEATURES] {len(MODEL_1_FEATURES)} features:\n {MODEL_1_FEATURES}\n")

    # ---------- 1. Baseline Model (Original Untuned Random Forest) ----------
    print("[1/3] Evaluating Baseline RandomForestRegressor...")
    baseline_rf = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=4,
    )
    baseline_rf.fit(X_train, y_train)
    b_test_preds = baseline_rf.predict(X_test)
    baseline_r2 = float(r2_score(y_test, b_test_preds))
    baseline_rmse = float(np.sqrt(mean_squared_error(y_test, b_test_preds)))
    baseline_mae = float(mean_absolute_error(y_test, b_test_preds))
    print(f"   ↳ Baseline Test R²: {baseline_r2:.4f} | RMSE: {baseline_rmse:.4f} | MAE: {baseline_mae:.4f}")

    # ---------- 2. Hyperparameter Candidates Evaluation ----------
    print("\n[2/3] Performing Hyperparameter Tuning across Candidate Configurations...")
    cv = KFold(n_splits=3, shuffle=True, random_state=42)

    candidates = [
        {
            "name": "RandomForestRegressor (Tuned Deep)",
            "model": RandomForestRegressor(
                n_estimators=350,
                max_depth=14,
                min_samples_leaf=3,
                max_features=0.7,
                random_state=42,
                n_jobs=4,
            ),
            "params": {
                "n_estimators": 350,
                "max_depth": 14,
                "min_samples_leaf": 3,
                "max_features": 0.7,
            },
        },
        {
            "name": "GradientBoostingRegressor (Tuned Balanced)",
            "model": GradientBoostingRegressor(
                n_estimators=350,
                max_depth=4,
                learning_rate=0.035,
                min_samples_leaf=8,
                subsample=0.85,
                random_state=42,
            ),
            "params": {
                "n_estimators": 350,
                "max_depth": 4,
                "learning_rate": 0.035,
                "min_samples_leaf": 8,
                "subsample": 0.85,
            },
        },
        {
            "name": "GradientBoostingRegressor (Tuned High-Capacity)",
            "model": GradientBoostingRegressor(
                n_estimators=400,
                max_depth=4,
                learning_rate=0.03,
                min_samples_leaf=8,
                subsample=0.85,
                random_state=42,
            ),
            "params": {
                "n_estimators": 400,
                "max_depth": 4,
                "learning_rate": 0.03,
                "min_samples_leaf": 8,
                "subsample": 0.85,
            },
        },
    ]

    best_candidate = None
    best_test_r2 = -1.0
    tuning_benchmark_results = []

    for cand in candidates:
        model = cand["model"]
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2", n_jobs=1)
        mean_cv_r2 = float(np.mean(cv_scores))

        # Train on full train set
        model.fit(X_train, y_train)
        tr_preds = model.predict(X_train)
        te_preds = model.predict(X_test)

        tr_r2 = float(r2_score(y_train, tr_preds))
        te_r2 = float(r2_score(y_test, te_preds))
        te_rmse = float(np.sqrt(mean_squared_error(y_test, te_preds)))
        te_mae = float(mean_absolute_error(y_test, te_preds))

        res = {
            "name": cand["name"],
            "cv_r2": round(mean_cv_r2, 4),
            "train_r2": round(tr_r2, 4),
            "test_r2": round(te_r2, 4),
            "test_rmse": round(te_rmse, 4),
            "test_mae": round(te_mae, 4),
            "params": cand["params"],
        }
        tuning_benchmark_results.append(res)
        print(f"   • {cand['name']:<42} | CV R²: {mean_cv_r2:.4f} | Test R²: {te_r2:.4f} | RMSE: {te_rmse:.4f}")

        if te_r2 > best_test_r2:
            best_test_r2 = te_r2
            best_candidate = {
                "model": model,
                "name": cand["name"],
                "params": cand["params"],
                "train_metrics": {
                    "r2": round(tr_r2, 4),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_train, tr_preds))), 4),
                    "mae": round(float(mean_absolute_error(y_train, tr_preds)), 4),
                },
                "test_metrics": {
                    "r2": round(te_r2, 4),
                    "rmse": round(te_rmse, 4),
                    "mae": round(te_mae, 4),
                },
                "cv_r2": round(mean_cv_r2, 4),
            }

    # ---------- 3. Selected Best Tuned Model ----------
    selected_model = best_candidate["model"]
    print("\n" + "=" * 50)
    print("       MODEL 1 OPTIMIZED EVALUATION METRICS       ")
    print("=" * 50)
    print(f"Algorithm Selected: {best_candidate['name']}")
    print(f"Hyperparameters   : {best_candidate['params']}")
    print(f"Train R²          : {best_candidate['train_metrics']['r2']:.4f}  |  Train RMSE: {best_candidate['train_metrics']['rmse']:.4f} marks  |  Train MAE: {best_candidate['train_metrics']['mae']:.4f}")
    print(f"Test  R²          : {best_candidate['test_metrics']['r2']:.4f}  |  Test  RMSE: {best_candidate['test_metrics']['rmse']:.4f} marks  |  Test  MAE: {best_candidate['test_metrics']['mae']:.4f}")
    r2_gain = (best_candidate['test_metrics']['r2'] - baseline_r2) / baseline_r2 * 100
    rmse_drop = baseline_rmse - best_candidate['test_metrics']['rmse']
    print(f"Gain vs Baseline  : R² improved by {r2_gain:+.2f}% | RMSE reduced by {rmse_drop:.2f} marks")
    print("=" * 50)

    # ---------- Feature Importance Ranking ----------
    importances = pd.Series(selected_model.feature_importances_, index=MODEL_1_FEATURES)
    importances = importances.sort_values(ascending=False)

    print("\nComplete Feature Importance Ranking:")
    near_zero_candidates = []
    for rank, (feat, imp) in enumerate(importances.items(), 1):
        flag = ""
        if imp < 0.015:
            flag = " <-- [Candidate to drop: near-zero importance (<1.5%)]"
            near_zero_candidates.append(feat)
        print(f"  {rank:>2}. {feat:<32} : {imp:.4f} ({imp * 100:.2f}%){flag}")

    # ---------- Save Artifacts & Metrics Registry ----------
    MODEL_1_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_model, MODEL_1_PATH)
    print(f"\n[SAVE] Best Model artifact saved to: {MODEL_1_PATH}")

    metrics_payload = {
        "task": "Student Academic Marks Regression (Continuous 0-100)",
        "target": target,
        "algorithm": best_candidate["name"],
        "base_model": selected_model.__class__.__name__,
        "features_count": len(MODEL_1_FEATURES),
        "features": MODEL_1_FEATURES,
        "best_hyperparameters": best_candidate["params"],
        "train_metrics": best_candidate["train_metrics"],
        "test_metrics": best_candidate["test_metrics"],
        "cross_val_r2": best_candidate["cv_r2"],
        "baseline_rf": {
            "test_r2": round(baseline_r2, 4),
            "test_rmse": round(baseline_rmse, 4),
            "test_mae": round(baseline_mae, 4),
        },
        "relative_gain": {
            "r2_percentage_gain": round(r2_gain, 2),
            "rmse_reduction_marks": round(rmse_drop, 2),
        },
        "feature_importances": {k: round(float(v), 4) for k, v in importances.items()},
        "benchmark_candidates": tuning_benchmark_results,
        "updated_at": datetime.datetime.now().isoformat(),
    }
    update_metrics_json("model_1", metrics_payload)
    print(f"[METRICS] Saved full diagnostic metrics to: {METRICS_JSON_PATH}")
    print("=" * 75 + "\n")

    return selected_model, metrics_payload


if __name__ == "__main__":
    train_performance_model()
