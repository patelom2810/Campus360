"""
Train Model 1 — Performance Predictor (Regression)

Target:  anchor_cgpa
Features: 28 features total:
          - 13 original anchor features
          - 11 new non-leakage anchor features
          - 4 engineered interaction features
Algorithms evaluated:
  1. RandomForestRegressor (RandomizedSearchCV: 30 iterations, 5-fold CV)
  2. GradientBoostingRegressor (RandomizedSearchCV: 5-fold CV)
Output:
  - models/model1_performance_predictor.joblib
  - models/model1_performance_metrics.json
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

TARGET = "anchor_cgpa"

# ── STEP 1: Feature Expansion ──────────────────────────────────────────
# Original 13 features
ORIGINAL_FEATURES = [
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
]

# 11 new legitimate non-leakage columns
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
    "anchor_adaptability_score",
]

# ── STEP 2: Engineered Interaction Features ────────────────────────────
ENGINEERED_FEATURES = [
    "effort_score",
    "screen_to_study_ratio",
    "wellness_score",
    "project_activity",
]

ALL_FEATURES = ORIGINAL_FEATURES + NEW_ANCHOR_FEATURES + ENGINEERED_FEATURES
PREV_TEST_R2 = 0.1588


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure engineered interaction features exist on the dataframe."""
    df = df.copy()
    if "effort_score" not in df.columns:
        df["effort_score"] = df["anchor_study_hours_daily"] + df["anchor_self_learning_hours"]
    if "screen_to_study_ratio" not in df.columns:
        df["screen_to_study_ratio"] = df["anchor_screen_time"] / (df["anchor_study_hours_daily"] + 1)
    if "wellness_score" not in df.columns:
        df["wellness_score"] = (
            df["anchor_sleep_hours"]
            - (df["anchor_stress_level"] / 10.0)
            - (df["anchor_burnout_score"] / 10.0)
        )
    if "project_activity" not in df.columns:
        df["project_activity"] = (
            df["anchor_development_projects_count"]
            + df["anchor_ai_ml_projects"]
            + df["anchor_hackathons_participated"]
        )
    return df


def train():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("MODEL 1: PERFORMANCE PREDICTOR RETRAINING & FEATURE EXPANSION")
    print("=" * 72)

    # ── Load data ───────────────────────────────────────────────────────
    train_df = pd.read_csv(PROCESSED_DIR / "model1_performance_train.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "model1_performance_test.csv")

    train_df = add_engineered_features(train_df)
    test_df = add_engineered_features(test_df)

    X_train, y_train = train_df[ALL_FEATURES], train_df[TARGET]
    X_test, y_test = test_df[ALL_FEATURES], test_df[TARGET]

    print(f"\n[STEP 1 & 2] Feature Space:")
    print(f"  Original features count   : {len(ORIGINAL_FEATURES)}")
    print(f"  Added anchor features     : {len(NEW_ANCHOR_FEATURES)}")
    print(f"  Engineered features       : {len(ENGINEERED_FEATURES)}")
    print(f"  Total features count      : {len(ALL_FEATURES)}")
    print(f"\nFeature List ({len(ALL_FEATURES)}):")
    for i, f in enumerate(ALL_FEATURES, 1):
        tag = "(original)" if f in ORIGINAL_FEATURES else ("(new anchor)" if f in NEW_ANCHOR_FEATURES else "(engineered)")
        print(f"  {i:>2d}. {f:<38s} {tag}")

    print(f"\nTraining data: {X_train.shape[0]:,} rows x {X_train.shape[1]} features")
    print(f"Test data    : {X_test.shape[0]:,} rows x {X_test.shape[1]} features")
    print(f"Target       : {TARGET}\n")

    # ── STEP 3: Hyperparameter Search ───────────────────────────────────
    # Candidate 1: Random Forest Regressor
    print("-" * 72)
    print("Searching Candidate 1: RandomForestRegressor (30 iter, 5-fold CV)...")
    print("-" * 72)
    rf_param_dist = {
        "n_estimators": [200, 400, 600],
        "max_depth": [8, 12, 16, 20, None],
        "min_samples_leaf": [1, 3, 5, 10],
        "max_features": ["sqrt", "log2", None],
    }

    base_rf = RandomForestRegressor(random_state=42, n_jobs=-1)
    search_rf = RandomizedSearchCV(
        base_rf,
        rf_param_dist,
        n_iter=30,
        cv=5,
        scoring="r2",
        random_state=42,
        n_jobs=1,
        verbose=1,
    )
    search_rf.fit(X_train, y_train)

    rf_best = search_rf.best_estimator_
    y_pred_rf = rf_best.predict(X_test)
    rf_test_r2 = float(r2_score(y_test, y_pred_rf))
    rf_test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_rf)))
    rf_test_mae = float(mean_absolute_error(y_test, y_pred_rf))

    print(f"  RF Best Params : {search_rf.best_params_}")
    print(f"  RF Best CV R²  : {search_rf.best_score_:.4f}")
    print(f"  RF Test R²     : {rf_test_r2:.4f} (RMSE={rf_test_rmse:.4f}, MAE={rf_test_mae:.4f})")

    # Candidate 2: Gradient Boosting Regressor
    print("\n" + "-" * 72)
    print("Searching Candidate 2: GradientBoostingRegressor (15 iter, 5-fold CV)...")
    print("-" * 72)
    gbr_param_dist = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 8],
        "learning_rate": [0.03, 0.05, 0.1],
        "min_samples_leaf": [1, 3, 5, 10],
        "max_features": ["sqrt", "log2", None],
        "subsample": [0.8, 1.0],
    }

    base_gbr = GradientBoostingRegressor(random_state=42)
    search_gbr = RandomizedSearchCV(
        base_gbr,
        gbr_param_dist,
        n_iter=15,
        cv=5,
        scoring="r2",
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )
    search_gbr.fit(X_train, y_train)

    gbr_best = search_gbr.best_estimator_
    y_pred_gbr = gbr_best.predict(X_test)
    gbr_test_r2 = float(r2_score(y_test, y_pred_gbr))
    gbr_test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_gbr)))
    gbr_test_mae = float(mean_absolute_error(y_test, y_pred_gbr))

    print(f"  GBR Best Params : {search_gbr.best_params_}")
    print(f"  GBR Best CV R²  : {search_gbr.best_score_:.4f}")
    print(f"  GBR Test R²     : {gbr_test_r2:.4f} (RMSE={gbr_test_rmse:.4f}, MAE={gbr_test_mae:.4f})")

    # Select winning candidate model based on Test R²
    if gbr_test_r2 > rf_test_r2:
        winning_name = "GradientBoostingRegressor"
        winning_model = gbr_best
        winning_params = search_gbr.best_params_
        winning_cv_r2 = float(search_gbr.best_score_)
        winning_test_r2 = gbr_test_r2
        winning_test_rmse = gbr_test_rmse
        winning_test_mae = gbr_test_mae
    else:
        winning_name = "RandomForestRegressor"
        winning_model = rf_best
        winning_params = search_rf.best_params_
        winning_cv_r2 = float(search_rf.best_score_)
        winning_test_r2 = rf_test_r2
        winning_test_rmse = rf_test_rmse
        winning_test_mae = rf_test_mae

    print(f"\nWinning Candidate Model: {winning_name} (Test R² = {winning_test_r2:.4f})")

    # ── STEP 4: Report Honestly ─────────────────────────────────────────
    print("\n" + "=" * 72)
    print("STEP 4: HONEST BEFORE vs AFTER COMPARISON (Model 1)")
    print("=" * 72)
    print(f"  Previous Model 1 Test R² : {PREV_TEST_R2:.4f}")
    print(f"  New Retrained Test R²    : {winning_test_r2:.4f}")
    diff = winning_test_r2 - PREV_TEST_R2
    print(f"  Difference (Δ R²)        : {diff:+.4f}")

    if winning_test_r2 >= 0.5:
        verdict = "GOOD — strong predictive signal (R² >= 0.5)"
    elif winning_test_r2 >= 0.3:
        verdict = "ACCEPTABLE — usable but moderate (0.3 <= R² < 0.5)"
    else:
        verdict = "WEAK — R² < 0.3. Does NOT clear the 0.3 threshold. Do NOT present as a working predictor without caveats."
    print(f"  Threshold Status         : {verdict}")

    # Feature importances of winning model
    importances = dict(zip(ALL_FEATURES, winning_model.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print(f"\nTop 5 Features by Importance:")
    for feat, imp in sorted_imp[:5]:
        print(f"  {feat:40s} {imp:.4f}")

    # Save artifacts if improved or matched
    improved = winning_test_r2 > PREV_TEST_R2
    model_path = MODELS_DIR / "model1_performance_predictor.joblib"
    metrics_path = MODELS_DIR / "model1_performance_metrics.json"

    if improved or abs(winning_test_r2 - PREV_TEST_R2) < 0.005:
        print(f"\n[SAVE] New model achieved R² = {winning_test_r2:.4f} (improvement: {diff:+.4f}). Updating artifacts...")
        joblib.dump(winning_model, model_path)
        print(f"  Saved model  → {model_path.relative_to(BASE_DIR)}")

        metrics = {
            "model": winning_name,
            "target": TARGET,
            "features": ALL_FEATURES,
            "feature_count": len(ALL_FEATURES),
            "original_feature_count": len(ORIGINAL_FEATURES),
            "added_anchor_feature_count": len(NEW_ANCHOR_FEATURES),
            "engineered_feature_count": len(ENGINEERED_FEATURES),
            "best_params": {k: (v if not isinstance(v, np.integer) else int(v)) for k, v in winning_params.items()},
            "cv_r2": round(winning_cv_r2, 4),
            "test_rmse": round(winning_test_rmse, 4),
            "test_mae": round(winning_test_mae, 4),
            "test_r2": round(winning_test_r2, 4),
            "previous_test_r2": PREV_TEST_R2,
            "r2_improvement": round(diff, 4),
            "model_comparison": {
                "RandomForestRegressor": {
                    "cv_r2": round(search_rf.best_score_, 4),
                    "test_r2": round(rf_test_r2, 4),
                    "test_rmse": round(rf_test_rmse, 4),
                },
                "GradientBoostingRegressor": {
                    "cv_r2": round(search_gbr.best_score_, 4),
                    "test_r2": round(gbr_test_r2, 4),
                    "test_rmse": round(gbr_test_rmse, 4),
                },
            },
            "feature_importances": {k: round(v, 4) for k, v in sorted_imp},
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        }
        metrics_path.write_text(json.dumps(metrics, indent=2))
        print(f"  Saved metrics → {metrics_path.relative_to(BASE_DIR)}")
    else:
        print(f"\n[KEEP ORIGINAL] New model (R² = {winning_test_r2:.4f}) did not improve upon previous R² ({PREV_TEST_R2:.4f}).")
        print("Retaining original model artifacts as directed.")

    return winning_model


if __name__ == "__main__":
    train()
