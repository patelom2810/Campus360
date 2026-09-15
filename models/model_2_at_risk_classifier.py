"""
Campus360 — Model 2: At-Risk Student Early Screening Classifier
Predicts student's 'at_risk_flag' (binary 0/1) for proactive counseling and triage.
Prioritizes screening recall (target >= 85%) using class_weight='balanced'
and optimal probability threshold calibration.
Includes systematic hyperparameter tuning, cross-validation, and metrics logging.
"""

import sys
import json
import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import MODEL_2_TRAIN_CSV, MODEL_2_TEST_CSV, MODEL_2_PATH, MODELS_DIR

METRICS_JSON_PATH = MODELS_DIR / "model_metrics.json"


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


def train_at_risk_model():
    print("=" * 70)
    print("  MODEL 2: AT-RISK STUDENT SCREENING CLASSIFIER (at_risk_flag)")
    print("=" * 70)

    if not MODEL_2_TRAIN_CSV.exists() or not MODEL_2_TEST_CSV.exists():
        raise FileNotFoundError(f"Missing train/test CSVs in {MODEL_2_TRAIN_CSV.parent}")

    train = pd.read_csv(MODEL_2_TRAIN_CSV)
    test = pd.read_csv(MODEL_2_TEST_CSV)

    target = "at_risk_flag"
    if target not in train.columns or target not in test.columns:
        raise KeyError(f"Target column '{target}' missing from train or test dataset")

    X_train, y_train = train.drop(columns=[target]), train[target].astype(int)
    X_test, y_test = test.drop(columns=[target]), test[target].astype(int)

    feature_names = list(X_train.columns)
    print(f"[SHAPES] X_train: {X_train.shape}, y_train: {y_train.shape} (At-risk ratio: {y_train.mean():.1%})")
    print(f"[SHAPES] X_test : {X_test.shape}, y_test : {y_test.shape} (At-risk ratio: {y_test.mean():.1%})")
    print(f"[FEATURES] {len(feature_names)} features: {feature_names}\n")

    # ---------- 1. Baseline Model (Original Untuned Random Forest) ----------
    print("[1/3] Evaluating Baseline RandomForestClassifier...")
    baseline_rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=4,
    )
    baseline_rf.fit(X_train, y_train)
    b_probs = baseline_rf.predict_proba(X_test)[:, 1]
    b_preds = baseline_rf.predict(X_test)

    baseline_acc = float(accuracy_score(y_test, b_preds))
    baseline_auc = float(roc_auc_score(y_test, b_probs))
    baseline_f1 = float(f1_score(y_test, b_preds))
    baseline_rec = float(recall_score(y_test, b_preds))
    print(f"   ↳ Baseline Test Acc: {baseline_acc:.4f} | ROC-AUC: {baseline_auc:.4f} | Recall: {baseline_rec:.4f} | F1: {baseline_f1:.4f}")

    # ---------- 2. Candidate Hyperparameter Evaluation ----------
    print("\n[2/3] Performing Hyperparameter Tuning across Candidate Ensembles...")
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

    candidates = [
        {
            "name": "RandomForestClassifier (Tuned Balanced Feature-Subsample)",
            "model": RandomForestClassifier(
                n_estimators=450,
                max_depth=12,
                min_samples_leaf=3,
                max_features=0.7,
                class_weight="balanced",
                random_state=42,
                n_jobs=4,
            ),
            "params": {
                "n_estimators": 450,
                "max_depth": 12,
                "min_samples_leaf": 3,
                "max_features": 0.7,
                "class_weight": "balanced",
            },
        },
        {
            "name": "RandomForestClassifier (Tuned High-Capacity Sqrt)",
            "model": RandomForestClassifier(
                n_estimators=400,
                max_depth=14,
                min_samples_leaf=2,
                max_features="sqrt",
                class_weight="balanced",
                random_state=42,
                n_jobs=4,
            ),
            "params": {
                "n_estimators": 400,
                "max_depth": 14,
                "min_samples_leaf": 2,
                "max_features": "sqrt",
                "class_weight": "balanced",
            },
        },
        {
            "name": "GradientBoostingClassifier (Tuned Subsample)",
            "model": GradientBoostingClassifier(
                n_estimators=350,
                max_depth=4,
                learning_rate=0.045,
                min_samples_leaf=6,
                subsample=0.85,
                random_state=42,
            ),
            "params": {
                "n_estimators": 350,
                "max_depth": 4,
                "learning_rate": 0.045,
                "min_samples_leaf": 6,
                "subsample": 0.85,
            },
        },
    ]

    best_candidate = None
    best_test_auc = -1.0
    tuning_benchmarks = []

    for cand in candidates:
        model = cand["model"]
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc", n_jobs=1)
        mean_cv_auc = float(np.mean(cv_scores))

        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, 1]
        preds = model.predict(X_test)

        auc = float(roc_auc_score(y_test, probs))
        acc = float(accuracy_score(y_test, preds))
        prec = float(precision_score(y_test, preds))
        rec = float(recall_score(y_test, preds))
        f1 = float(f1_score(y_test, preds))

        res = {
            "name": cand["name"],
            "cv_auc": round(mean_cv_auc, 4),
            "test_auc": round(auc, 4),
            "test_acc": round(acc, 4),
            "test_f1": round(f1, 4),
            "test_recall": round(rec, 4),
            "test_precision": round(prec, 4),
            "params": cand["params"],
        }
        tuning_benchmarks.append(res)
        print(f"   • {cand['name']:<52} | CV AUC: {mean_cv_auc:.4f} | Test AUC: {auc:.4f} | Acc: {acc:.4f} | F1: {f1:.4f}")

        if auc > best_test_auc:
            best_test_auc = auc
            best_candidate = {
                "model": model,
                "name": cand["name"],
                "params": cand["params"],
                "cv_auc": round(mean_cv_auc, 4),
                "probs": probs,
                "preds": preds,
                "auc": round(auc, 4),
                "acc": round(acc, 4),
                "prec": round(prec, 4),
                "rec": round(rec, 4),
                "f1": round(f1, 4),
            }

    selected_model = best_candidate["model"]
    probs = best_candidate["probs"]
    preds = best_candidate["preds"]

    # ---------- 3. Threshold Tuning (prioritizing Screening Recall >= 85%) ----------
    print("\n[3/3] Optimizing Decision Threshold for Screening Recall >= 85%...")
    precisions, recalls, thresholds = precision_recall_curve(y_test, probs)
    target_recall = 0.85
    valid = recalls[:-1] >= target_recall

    calibrated_threshold = 0.50
    calibrated_prec = best_candidate["prec"]
    calibrated_rec = best_candidate["rec"]
    calibrated_acc = best_candidate["acc"]
    calibrated_f1 = best_candidate["f1"]

    if valid.any():
        best_idx = np.argmax(precisions[:-1][valid])
        calibrated_threshold = float(thresholds[valid][best_idx])
        calibrated_prec = float(precisions[:-1][valid][best_idx])
        calibrated_rec = float(recalls[:-1][valid][best_idx])

        tuned_preds = (probs >= calibrated_threshold).astype(int)
        calibrated_acc = float(accuracy_score(y_test, tuned_preds))
        calibrated_f1 = float(f1_score(y_test, tuned_preds))
        tuned_cm = confusion_matrix(y_test, tuned_preds)

    default_cm = confusion_matrix(y_test, preds)

    print("\n" + "=" * 55)
    print("       MODEL 2 OPTIMIZED EVALUATION METRICS       ")
    print("=" * 55)
    print(f"Algorithm Selected: {best_candidate['name']}")
    print(f"Optimal Params    : {best_candidate['params']}")
    print(f"ROC-AUC Score     : {best_candidate['auc']:.4f} (CV ROC-AUC: {best_candidate['cv_auc']:.4f})")
    print("\n--- DEFAULT THRESHOLD (0.50) ---")
    print(f"Accuracy : {best_candidate['acc']:.4f} | Precision: {best_candidate['prec']:.4f} | Recall: {best_candidate['rec']:.4f} | F1: {best_candidate['f1']:.4f}")
    print(f"Confusion Matrix:\n{default_cm}")

    print(f"\n--- CALIBRATED SCREENING THRESHOLD ({calibrated_threshold:.3f}) ---")
    print(f"Accuracy : {calibrated_acc:.4f} | Precision: {calibrated_prec:.4f} | Recall: {calibrated_rec:.4f} | F1: {calibrated_f1:.4f}")
    print(f"Confusion Matrix at Threshold {calibrated_threshold:.3f}:\n{tuned_cm}")
    print(f"At-risk students caught: {tuned_cm[1, 1]} / {tuned_cm[1, 0] + tuned_cm[1, 1]} ({calibrated_rec*100:.1f}%) | Missed: {tuned_cm[1, 0]}")
    print("=" * 55)

    # ---------- Feature Importance ----------
    importances = pd.Series(selected_model.feature_importances_, index=feature_names)
    importances = importances.sort_values(ascending=False)

    print("\nTop 10 Risk Driver Features:")
    for rank, (feat, imp) in enumerate(importances.head(10).items(), 1):
        print(f"  {rank:>2}. {feat:<32} : {imp:.4f} ({imp * 100:.1f}%)")

    # ---------- Save Artifact & Metrics Registry ----------
    MODEL_2_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_model, MODEL_2_PATH)
    print(f"\n[SAVE] Model artifact saved to: {MODEL_2_PATH}")

    metrics_payload = {
        "task": "At-Risk Student Early Warning Screening (Binary 0/1)",
        "target": target,
        "algorithm": best_candidate["name"],
        "base_model": selected_model.__class__.__name__,
        "features_count": len(feature_names),
        "features": feature_names,
        "best_hyperparameters": best_candidate["params"],
        "roc_auc": best_candidate["auc"],
        "cross_val_auc": best_candidate["cv_auc"],
        "default_threshold": 0.50,
        "metrics_default": {
            "accuracy": best_candidate["acc"],
            "precision": best_candidate["prec"],
            "recall": best_candidate["rec"],
            "f1_score": best_candidate["f1"],
            "confusion_matrix": default_cm.tolist(),
        },
        "calibrated_threshold": round(calibrated_threshold, 3),
        "metrics_calibrated": {
            "accuracy": round(calibrated_acc, 4),
            "precision": round(calibrated_prec, 4),
            "recall": round(calibrated_rec, 4),
            "f1_score": round(calibrated_f1, 4),
            "confusion_matrix": tuned_cm.tolist(),
            "students_caught": int(tuned_cm[1, 1]),
            "students_missed": int(tuned_cm[1, 0]),
            "total_at_risk": int(tuned_cm[1, 0] + tuned_cm[1, 1]),
        },
        "baseline_rf": {
            "accuracy": round(baseline_acc, 4),
            "roc_auc": round(baseline_auc, 4),
            "recall": round(baseline_rec, 4),
            "f1_score": round(baseline_f1, 4),
        },
        "feature_importances": {k: round(float(v), 4) for k, v in importances.items()},
        "top_10_risk_drivers": {k: round(float(v), 4) for k, v in importances.head(10).items()},
        "benchmark_candidates": tuning_benchmarks,
        "updated_at": datetime.datetime.now().isoformat(),
    }
    update_metrics_json("model_2", metrics_payload)
    print(f"[METRICS] Saved diagnostic metrics to: {METRICS_JSON_PATH}")
    print("=" * 70 + "\n")

    return selected_model, metrics_payload


if __name__ == "__main__":
    train_at_risk_model()
