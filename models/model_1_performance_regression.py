"""
Campus360 — Model 1: Student Next Semester Marks Performance Regression
Predicts student's 'next_semester_marks' using finalized 18 academic,
coursework, and lifestyle indicators.
Zero target leakage guarantee: omits previous_sgpa and previous_exam_average.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import MODEL_1_TRAIN_CSV, MODEL_1_TEST_CSV, MODEL_1_PATH

# 18 Finalized Features per KDAC-3 Problem Specification
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
    print(f"[FEATURES] {len(MODEL_1_FEATURES)} features:\n {MODEL_1_FEATURES}")

    # ---------- Model Training ----------
    print("\n[TRAINING] Fitting RandomForestRegressor (n_estimators=300, max_depth=12, min_samples_leaf=5)...")
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # ---------- Evaluate Train & Test ----------
    train_preds = model.predict(X_train)
    train_mae = mean_absolute_error(y_train, train_preds)
    train_rmse = np.sqrt(mean_squared_error(y_train, train_preds))
    train_r2 = r2_score(y_train, train_preds)

    test_preds = model.predict(X_test)
    test_mae = mean_absolute_error(y_test, test_preds)
    test_rmse = np.sqrt(mean_squared_error(y_test, test_preds))
    test_r2 = r2_score(y_test, test_preds)

    print("\n" + "=" * 50)
    print("       MODEL 1 EVALUATION METRICS       ")
    print("=" * 50)
    print(f"Train R²   : {train_r2:.4f}  |  Train RMSE: {train_rmse:.4f} marks  |  Train MAE: {train_mae:.4f}")
    print(f"Test  R²   : {test_r2:.4f}  |  Test  RMSE: {test_rmse:.4f} marks  |  Test  MAE: {test_mae:.4f}")
    print("=" * 50)

    # ---------- Feature Importance Ranking ----------
    importances = pd.Series(model.feature_importances_, index=MODEL_1_FEATURES)
    importances = importances.sort_values(ascending=False)

    print("\nComplete Feature Importance Ranking:")
    near_zero_candidates = []
    for rank, (feat, imp) in enumerate(importances.items(), 1):
        flag = ""
        if imp < 0.015:  # under 1.5% contribution
            flag = " <-- [Candidate to drop: near-zero importance (<1.5%)]"
            near_zero_candidates.append(feat)
        print(f"  {rank:>2}. {feat:<32} : {imp:.4f} ({imp * 100:.2f}%){flag}")

    if near_zero_candidates:
        print(f"\n[FLAGGED] {len(near_zero_candidates)} candidate features contributing < 1.5% of predictive power:")
        for c in near_zero_candidates:
            print(f"   • {c} ({importances[c]*100:.2f}%)")

    # ---------- Save Artifact ----------
    MODEL_1_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_1_PATH)
    print(f"\n[SAVE] 18-feature Model saved to {MODEL_1_PATH}")
    print("=" * 75 + "\n")

    return model, {
        "train_r2": train_r2,
        "train_rmse": train_rmse,
        "test_r2": test_r2,
        "test_rmse": test_rmse,
        "near_zero_candidates": near_zero_candidates,
        "feature_importances": importances.to_dict(),
    }


if __name__ == "__main__":
    train_performance_model()
