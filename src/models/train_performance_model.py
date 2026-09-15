"""
Train Model 1 — Performance Predictor (Regression)
Sole Production Model: 10-Feature Compact GradientBoostingRegressor

Target:  anchor_cgpa
Features (10):
  - anchor_dsa_problems_solved
  - anchor_study_hours_daily
  - anchor_communication_skills
  - anchor_aptitude_score
  - effort_score
  - screen_to_study_ratio
  - anchor_internships_completed
  - anchor_resume_score
  - anchor_screen_time
  - anchor_family_income_lpa

Output:
  - models/model1_performance_predictor.joblib
  - models/model1_performance_metrics.json
"""

import json
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "anchor_cgpa"

MODEL_1_FEATURES = [
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


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure engineered interaction features exist on the dataframe."""
    df = df.copy()
    if "effort_score" not in df.columns:
        df["effort_score"] = df["anchor_study_hours_daily"] + df["anchor_self_learning_hours"]
    if "screen_to_study_ratio" not in df.columns:
        df["screen_to_study_ratio"] = df["anchor_screen_time"] / (df["anchor_study_hours_daily"] + 1)
    return df


def train():
    print("=" * 80)
    print("TRAINING SOLE PRODUCTION MODEL 1: 10-FEATURE COMPACT REGRESSOR (anchor_cgpa)")
    print("=" * 80)

    train_path = PROCESSED_DIR / "model1_performance_train.csv"
    test_path = PROCESSED_DIR / "model1_performance_test.csv"

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    train_df = add_engineered_features(train_df)
    test_df = add_engineered_features(test_df)

    X_train = train_df[MODEL_1_FEATURES]
    y_train = train_df[TARGET]
    X_test = test_df[MODEL_1_FEATURES]
    y_test = test_df[TARGET]

    print(f"Training set: {len(X_train):,} rows | Test set: {len(X_test):,} rows")
    print(f"Features ({len(MODEL_1_FEATURES)}): {MODEL_1_FEATURES}")

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

    print("\n[EVALUATION RESULTS - Model 1 Compact GBR]")
    print(f"  Test R²      : {r2:.4f}")
    print(f"  Test RMSE    : {rmse:.4f}")
    print(f"  Test MAE     : {mae:.4f}")
    print(f"  5-Fold CV R² : {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
    print(f"  Training Time: {train_time:.2f}s")

    # Serialize
    m1_path = MODELS_DIR / "model1_performance_predictor.joblib"
    joblib.dump(gbr, m1_path)
    print(f"Saved production Model 1 to: {m1_path.relative_to(BASE_DIR)}")

    importances = dict(zip(MODEL_1_FEATURES, [round(float(x), 4) for x in gbr.feature_importances_]))

    metrics = {
        "model_name": "GradientBoostingRegressor (10-feature compact)",
        "target": TARGET,
        "feature_count": len(MODEL_1_FEATURES),
        "features": MODEL_1_FEATURES,
        "feature_importances": importances,
        "test_r2": round(float(r2), 4),
        "test_rmse": round(float(rmse), 4),
        "test_mae": round(float(mae), 4),
        "cv_5fold_r2_mean": round(float(cv_scores.mean()), 4),
        "cv_5fold_r2_std": round(float(cv_scores.std()), 4),
        "baseline_28feat_r2": 0.2096,
        "delta_r2_vs_baseline": round(float(r2 - 0.2096), 4),
        "training_time_seconds": round(float(train_time), 2),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    metrics_path = MODELS_DIR / "model1_performance_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved production Model 1 metrics to: {metrics_path.relative_to(BASE_DIR)}")

    return gbr, metrics


if __name__ == "__main__":
    train()
