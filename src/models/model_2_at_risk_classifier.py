"""
Model 2: At-Risk Student Early Screening Classifier
KDAC-3 — Student Academic Success, Subject Performance & Career Readiness Platform

Purpose:
  Early detection of students vulnerable to academic attrition or failure,
  prioritizing screening recall (target recall >= 0.85) to minimize false negatives.
  Uses balanced RandomForestClassifier trained on holistic behavioral, attendance,
  and academic risk indicators.

Data Sources:
  1. Local at_risk_dataset.csv / data/processed/at_risk_dataset.csv
  2. Primary DB: PostgreSQL analytical view 'at_risk_features_view'
  3. Fallback: data/processed/student_master_stitched.csv
"""

import json
import os
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from config.config import get_db_engine
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False


def load_dataset() -> pd.DataFrame:
    """Loads at-risk dataset from local CSV or PostgreSQL 'at_risk_features_view'."""
    # 1. Check local at_risk_dataset.csv in root or data/processed
    candidates = [
        BASE_DIR / "at_risk_dataset.csv",
        BASE_DIR / "data" / "processed" / "at_risk_dataset.csv",
        BASE_DIR / "data" / "at_risk_dataset.csv"
    ]
    for p in candidates:
        if p.exists():
            df = pd.read_csv(p)
            print(f"[DATA] Loaded {len(df):,} records from {p.name}")
            return df

    # 2. Try PostgreSQL view if local CSV not found
    if HAS_CONFIG:
        try:
            engine = get_db_engine()
            query = "SELECT * FROM at_risk_features_view;"
            df = pd.read_sql_query(query, con=engine)
            if "target_at_risk_flag" in df.columns:
                df.rename(columns={"target_at_risk_flag": "at_risk_flag"}, inplace=True)
            print(f"[DATA] Loaded {len(df):,} records from PostgreSQL 'at_risk_features_view'.")
            return df
        except Exception as e:
            print(f"[DATA WARNING] Could not query PostgreSQL ({e}). Falling back to stitched master.")

    # 3. Fallback to student_master_stitched.csv
    fallback_path = BASE_DIR / "data" / "processed" / "student_master_stitched.csv"
    if fallback_path.exists():
        df = pd.read_csv(fallback_path)
        print(f"[DATA] Loaded {len(df):,} records from {fallback_path.name}")
        return df

    raise FileNotFoundError("Could not find at_risk_dataset.csv or student_master_stitched.csv")


def main():
    print("=" * 80)
    print("        KDAC-3 — MODEL 2: AT-RISK STUDENT SCREENING CLASSIFIER          ")
    print("=" * 80)

    # ---------- Load ----------
    df = load_dataset()

    # Standardize target column
    if "target_at_risk_flag" in df.columns:
        df.rename(columns={"target_at_risk_flag": "at_risk_flag"}, inplace=True)

    target = "at_risk_flag"
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in dataset columns: {df.columns.tolist()}")

    # ---------- Feature / target split ----------
    # Drop student_id, target, and non-predictive metadata/leakage if present
    drop_cols = ["student_id", target, "performance_band", "next_semester_marks", "target_next_semester_marks"]
    meta_cols = ["enrollment_date", "survey_date", "submitted_at", "last_sync_time", "created_at", "updated_at"]
    drop_cols.extend(meta_cols)

    X = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Convert categoricals if any exist
    cat_cols = X.select_dtypes(include=["object"]).columns.tolist()
    if cat_cols:
        X = pd.get_dummies(X, columns=cat_cols, drop_first=True)

    y = df[target].astype(int)

    feature_names = X.columns.tolist()
    print(f"\n[FEATURES] Predictive features count: {len(feature_names)}")
    print(f"[FEATURES] List: {feature_names}\n")

    # ---------- Train/test split (stratified — keeps class balance in both sets) ----------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"[SPLIT] Training instances: {len(X_train):,} | Test instances: {len(X_test):,}")

    # Save train/test split CSVs for independent validation
    processed_dir = BASE_DIR / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    train_split_df = X_train.copy()
    train_split_df[target] = y_train
    test_split_df = X_test.copy()
    test_split_df[target] = y_test
    train_split_df.to_csv(processed_dir / "model2_atrisk_train.csv", index=False)
    test_split_df.to_csv(processed_dir / "model2_atrisk_test.csv", index=False)

    # ---------- Model ----------
    print("\n[TRAIN] Fitting RandomForestClassifier (300 estimators, max_depth=10, balanced)...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",   # important for a screening use-case: penalize missed at-risk cases
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # ---------- Evaluate ----------
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 40)
    print("       MODEL 2 EVALUATION METRICS       ")
    print("=" * 40)
    print("Classification report:")
    print(classification_report(y_test, preds, target_names=["Not At Risk", "At Risk"]))

    print("Confusion matrix:")
    cm = confusion_matrix(y_test, preds)
    print(cm)

    auc = roc_auc_score(y_test, probs)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    f1 = f1_score(y_test, preds)
    print(f"\nROC-AUC  : {auc:.3f}")
    print(f"Accuracy : {acc:.3f}")
    print(f"Recall   : {rec:.3f}")
    print(f"Precision: {prec:.3f}")
    print(f"F1 Score : {f1:.3f}")
    print("=" * 40)

    # ---------- Threshold tuning (screening use case: prioritize recall) ----------
    # Default threshold is 0.5 -- for a "flag at-risk students" tool, you usually
    # want to catch more true at-risk students even at the cost of some false alarms.
    precisions, recalls, thresholds = precision_recall_curve(y_test, probs)
    target_recall = 0.85
    valid = recalls[:-1] >= target_recall
    best_threshold = 0.5
    calibrated_prec = prec
    calibrated_rec = rec
    if valid.any():
        best_idx = np.argmax(precisions[:-1][valid])
        best_threshold = float(thresholds[valid][best_idx])
        calibrated_prec = float(precisions[:-1][valid][best_idx])
        calibrated_rec = float(recalls[:-1][valid][best_idx])
        print(f"\nSuggested threshold for recall >= {target_recall}: {best_threshold:.3f}")
        print(f"  At tuned threshold -> Precision: {calibrated_prec:.3f} | Recall: {calibrated_rec:.3f}")

    # ---------- Feature importance ----------
    importances = pd.Series(model.feature_importances_, index=X.columns)
    importances = importances.sort_values(ascending=False)
    print("\nTop 10 risk drivers:")
    for rank, (feat, imp) in enumerate(importances.head(10).items(), 1):
        print(f"  {rank:>2}. {feat:<30} : {imp:.4f} ({imp*100:.1f}%)")

    # ---------- Save Model & Artifacts (.joblib and .pkl) ----------
    models_dir = BASE_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    root_model_joblib = BASE_DIR / "at_risk_classifier_model.joblib"
    root_model_pkl = BASE_DIR / "at_risk_classifier_model.pkl"
    models_dir_joblib = models_dir / "at_risk_classifier_model.joblib"
    models_dir_classifier = models_dir / "model2_atrisk_classifier.joblib"
    models_dir_pkl = models_dir / "at_risk_classifier_model.pkl"

    # Save joblib binaries
    joblib.dump(model, root_model_joblib)
    joblib.dump(model, models_dir_joblib)
    joblib.dump(model, models_dir_classifier)

    # Save pkl binaries
    joblib.dump(model, root_model_pkl)
    joblib.dump(model, models_dir_pkl)

    # Save bundle and metrics JSON
    metrics = {
        "target": target,
        "decision_threshold": 0.50,
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "roc_auc": float(auc),
        "test_accuracy": float(acc),
        "test_precision": float(prec),
        "test_recall": float(rec),
        "test_f1": float(f1),
        "test_roc_auc": float(auc),
        "test_precision_class1": float(prec),
        "test_recall_class1": float(rec),
        "screening_target_recall": target_recall,
        "calibrated_threshold": float(best_threshold),
        "calibrated_precision": float(calibrated_prec),
        "calibrated_recall": float(calibrated_rec),
        "confusion_matrix": cm.tolist(),
        "features": feature_names,
        "top_features": {k: float(v) for k, v in importances.head(10).items()}
    }

    bundle = {
        "model": model,
        "features": feature_names,
        "target": target,
        "metrics": metrics,
        "calibrated_threshold": float(best_threshold)
    }

    bundle_joblib = models_dir / "model_2_at_risk_classifier_bundle.joblib"
    bundle_pkl = models_dir / "model_2_at_risk_classifier_bundle.pkl"
    metrics_json = models_dir / "model2_atrisk_metrics.json"

    joblib.dump(bundle, bundle_joblib)
    joblib.dump(bundle, bundle_pkl)

    with open(metrics_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n[SAVE] Model saved to: {root_model_joblib.name} & {root_model_pkl.name}")
    print(f"[SAVE] Model saved to: models/{models_dir_joblib.name}")
    print(f"[SAVE] Model saved to: models/{models_dir_classifier.name}")
    print(f"[SAVE] Deployment bundle saved to: models/{bundle_joblib.name}")
    print(f"[SAVE] Metrics JSON saved to: models/{metrics_json.name}")
    print("=" * 80 + "\n")
    return model, bundle


if __name__ == "__main__":
    main()
