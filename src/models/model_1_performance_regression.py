"""
Model 1: Student Next Semester Marks Performance Regression
KDAC-3 — Student Academic Success, Subject Performance & Career Readiness Platform

Purpose:
  Predicts student's 'next_semester_marks' using academic history, coursework engagement,
  component exam assessments, attendance, and lifestyle indicators.
  Strictly avoids target leakage by dropping 'performance_band' and 'student_id'.

Data Sources:
  1. Primary: PostgreSQL analytical view 'performance_features_view'
  2. Fallback: data/processed/student_master_stitched.csv
"""

import os
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Add repo root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from config.config import get_db_engine
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False


def load_dataset() -> pd.DataFrame:
    """Loads student performance features from PostgreSQL or local processed CSV."""
    df = None
    if HAS_CONFIG:
        try:
            engine = get_db_engine()
            query = "SELECT * FROM performance_features_view;"
            df = pd.read_sql_query(query, con=engine)
            print(f"[DATA] Loaded {len(df):,} records from PostgreSQL 'performance_features_view'.")
        except Exception as e:
            print(f"[DATA WARNING] Could not query PostgreSQL ({e}). Falling back to local CSV.")
            
    if df is None or df.empty:
        csv_path = BASE_DIR / "data" / "processed" / "student_master_stitched.csv"
        if not csv_path.exists():
            csv_path = BASE_DIR / "data" / "raw" / "2_exam_marks.csv"
        df = pd.read_csv(csv_path)
        print(f"[DATA] Loaded {len(df):,} records from local file: {csv_path.name}")
        
    return df


def main():
    print("=" * 80)
    print("      KDAC-3 — MODEL 1: NEXT SEMESTER MARKS PERFORMANCE REGRESSION      ")
    print("=" * 80)
    
    # ---------- Load ----------
    df = load_dataset()
    
    # Standardize target column name
    if "target_next_semester_marks" in df.columns:
        df.rename(columns={"target_next_semester_marks": "next_semester_marks"}, inplace=True)
        
    target = "next_semester_marks"
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in dataset columns: {df.columns.tolist()}")
        
    # ---------- Feature / target split ----------
    # performance_band is directly derived from target -> severe leakage, drop it!
    # student_id is an identifier -> drop it
    drop_cols = ["student_id", "performance_band", target]
    
    # Also drop any non-feature date/meta columns if present
    meta_cols = ["enrollment_date", "survey_date", "submitted_at", "last_sync_time", "created_at", "updated_at"]
    drop_cols.extend([c for c in meta_cols if c in df.columns])
    
    # Select only relevant features present in df
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    
    # Keep only numeric columns or encode categoricals
    categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
    if categorical_cols:
        print(f"[PREPROCESS] One-hot encoding categorical features: {categorical_cols}")
        X = pd.get_dummies(X, columns=categorical_cols, drop_first=True)
        
    y = df[target]
    
    feature_names = X.columns.tolist()
    print(f"\n[FEATURES] Total predictive features: {len(feature_names)}")
    print(f"[FEATURES] List: {feature_names}\n")

    # ---------- Train/test split ----------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"[SPLIT] Training instances: {len(X_train):,} | Test instances: {len(X_test):,}")

    # Save train/test split CSVs for independent validation
    processed_dir = BASE_DIR / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    train_split_df = X_train.copy()
    train_split_df[target] = y_train
    test_split_df = X_test.copy()
    test_split_df[target] = y_test
    train_split_df.to_csv(processed_dir / "model1_performance_train.csv", index=False)
    test_split_df.to_csv(processed_dir / "model1_performance_test.csv", index=False)

    # ---------- Model ----------
    print("\n[TRAIN] Fitting RandomForestRegressor (300 estimators, max_depth=12)...")
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # ---------- Evaluate ----------
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)

    print("\n" + "=" * 40)
    print("       MODEL 1 EVALUATION METRICS       ")
    print("=" * 40)
    print(f"MAE  : {mae:.2f} marks")
    print(f"RMSE : {rmse:.2f} marks")
    print(f"R²   : {r2:.3f}")
    print("=" * 40)

    # ---------- Feature Importance ----------
    importances = pd.Series(model.feature_importances_, index=X.columns)
    importances = importances.sort_values(ascending=False)
    print("\nTop 10 predictive features (Tree MDI Importance):")
    for rank, (feat, imp) in enumerate(importances.head(10).items(), 1):
        print(f"  {rank:>2}. {feat:<30} : {imp:.4f} ({imp*100:.1f}%)")

    # ---------- SHAP Explainability ----------
    try:
        import shap
        print("\n[EXPLAINABILITY] Calculating TreeExplainer SHAP values on test sample...")
        sample_test = X_test.iloc[:200]
        explainer = shap.TreeExplainer(model)
        shap_values = explainer(sample_test)
        
        # Mean absolute SHAP value across sample
        mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
        shap_importance = pd.Series(mean_abs_shap, index=X.columns).sort_values(ascending=False)
        print("\nTop 5 features by Mean |SHAP| Value:")
        for rank, (feat, val) in enumerate(shap_importance.head(5).items(), 1):
            print(f"  {rank:>2}. {feat:<30} : {val:.4f}")
    except Exception as e:
        print(f"[NOTE] SHAP explanation note: {e}")

    # ---------- Save Model & Artifacts ----------
    models_dir = BASE_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model in joblib and pkl format in root and models/ directory
    root_model_joblib = BASE_DIR / "next_semester_marks_model.joblib"
    root_model_pkl = BASE_DIR / "next_semester_marks_model.pkl"
    models_dir_joblib = models_dir / "next_semester_marks_model.joblib"
    models_dir_predictor = models_dir / "model1_performance_predictor.joblib"
    models_dir_pkl = models_dir / "next_semester_marks_model.pkl"
    
    joblib.dump(model, root_model_joblib)
    joblib.dump(model, root_model_pkl)
    joblib.dump(model, models_dir_joblib)
    joblib.dump(model, models_dir_predictor)
    joblib.dump(model, models_dir_pkl)
    
    # Save metadata bundle (model + features + metrics)
    metrics_dict = {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "test_mae": float(mae),
        "test_rmse": float(rmse),
        "test_r2": float(r2),
    }
    bundle = {
        "model": model,
        "features": feature_names,
        "target": target,
        "metrics": metrics_dict,
        "top_features": {k: float(v) for k, v in importances.head(10).items()}
    }
    bundle_pkl_path = models_dir / "model_1_performance_regression_bundle.pkl"
    bundle_joblib_path = models_dir / "model_1_performance_regression_bundle.joblib"
    metrics_json_path = models_dir / "model1_performance_metrics.json"
    
    joblib.dump(bundle, bundle_pkl_path)
    joblib.dump(bundle, bundle_joblib_path)
    
    import json
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(bundle["metrics"] | {"features": feature_names, "target": target, "top_features": bundle["top_features"]}, f, indent=2)
    
    print(f"\n[SAVE] Model saved to: {root_model_joblib.name} & {root_model_pkl.name}")
    print(f"[SAVE] Model saved to: models/{models_dir_joblib.name}")
    print(f"[SAVE] Model saved to: models/{models_dir_predictor.name}")
    print(f"[SAVE] Deployment bundle saved to: models/{bundle_joblib_path.name}")
    print(f"[SAVE] Metrics JSON saved to: models/{metrics_json_path.name}")
    print("=" * 80 + "\n")
    return model, bundle


if __name__ == "__main__":
    main()
