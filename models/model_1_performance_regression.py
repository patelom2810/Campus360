"""
Campus360 — Model 1: Student Next Semester Marks Performance Regression
Predicts student's 'next_semester_marks' using academic history, coursework engagement,
exam assessments, attendance, and lifestyle indicators.
Reads train/test data from data/processed/ and saves trained model to models/.
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


def train_performance_model():
    print("=" * 70)
    print("  MODEL 1: STUDENT PERFORMANCE REGRESSION (next_semester_marks)")
    print("=" * 70)

    print(f"[DATA] Loading train: {MODEL_1_TRAIN_CSV}")
    print(f"[DATA] Loading test : {MODEL_1_TEST_CSV}")

    if not MODEL_1_TRAIN_CSV.exists() or not MODEL_1_TEST_CSV.exists():
        raise FileNotFoundError(f"Missing train/test CSVs in {MODEL_1_TRAIN_CSV.parent}")

    train = pd.read_csv(MODEL_1_TRAIN_CSV)
    test = pd.read_csv(MODEL_1_TEST_CSV)

    target = "next_semester_marks"
    if target not in train.columns or target not in test.columns:
        raise KeyError(f"Target column '{target}' missing from train or test dataset")

    X_train, y_train = train.drop(columns=[target]), train[target]
    X_test, y_test = test.drop(columns=[target]), test[target]

    print(f"[SHAPES] X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"[SHAPES] X_test : {X_test.shape}, y_test : {y_test.shape}")
    print(f"[FEATURES] {len(X_train.columns)} features: {list(X_train.columns)}")

    # ---------- Model Training ----------
    print("\n[TRAINING] Fitting RandomForestRegressor (n_estimators=300, max_depth=12)...")
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
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
    importances = pd.Series(model.feature_importances_, index=X_train.columns)
    importances = importances.sort_values(ascending=False)
    print("\nTop 10 predictive features:")
    for rank, (feat, imp) in enumerate(importances.head(10).items(), 1):
        print(f"  {rank:>2}. {feat:<32} : {imp:.4f} ({imp * 100:.1f}%)")

    # ---------- Save Artifact ----------
    MODEL_1_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_1_PATH)
    print(f"\n[SAVE] Model saved to {MODEL_1_PATH}")
    print("=" * 70 + "\n")

    return model, {"mae": mae, "rmse": rmse, "r2": r2, "top_features": importances.head(10).to_dict()}


if __name__ == "__main__":
    train_performance_model()
