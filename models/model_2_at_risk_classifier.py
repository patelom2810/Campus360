"""
Campus360 — Model 2: At-Risk Student Early Screening Classifier
Predicts student's 'at_risk_flag' (binary 0/1) for proactive counseling and triage.
Prioritizes screening recall (target >= 85%) using class_weight='balanced'.
Reads train/test data from data/processed/ and saves trained model to models/.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
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

from config.config import MODEL_2_TRAIN_CSV, MODEL_2_TEST_CSV, MODEL_2_PATH


def train_at_risk_model():
    print("=" * 70)
    print("  MODEL 2: AT-RISK STUDENT SCREENING CLASSIFIER (at_risk_flag)")
    print("=" * 70)

    print(f"[DATA] Loading train: {MODEL_2_TRAIN_CSV}")
    print(f"[DATA] Loading test : {MODEL_2_TEST_CSV}")

    if not MODEL_2_TRAIN_CSV.exists() or not MODEL_2_TEST_CSV.exists():
        raise FileNotFoundError(f"Missing train/test CSVs in {MODEL_2_TRAIN_CSV.parent}")

    train = pd.read_csv(MODEL_2_TRAIN_CSV)
    test = pd.read_csv(MODEL_2_TEST_CSV)

    target = "at_risk_flag"
    if target not in train.columns or target not in test.columns:
        raise KeyError(f"Target column '{target}' missing from train or test dataset")

    X_train, y_train = train.drop(columns=[target]), train[target].astype(int)
    X_test, y_test = test.drop(columns=[target]), test[target].astype(int)

    print(f"[SHAPES] X_train: {X_train.shape}, y_train: {y_train.shape} (At-risk ratio: {y_train.mean():.1%})")
    print(f"[SHAPES] X_test : {X_test.shape}, y_test : {y_test.shape} (At-risk ratio: {y_test.mean():.1%})")
    print(f"[FEATURES] {len(X_train.columns)} features: {list(X_train.columns)}")

    # ---------- Model Training ----------
    print("\n[TRAINING] Fitting RandomForestClassifier (n_estimators=300, max_depth=10, balanced)...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",   # penalize missing at-risk students more
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # ---------- Evaluate ----------
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 40)
    print("       MODEL 2 EVALUATION METRICS       ")
    print("=" * 40)
    print("Classification report (Default threshold = 0.50):")
    print(classification_report(y_test, preds, target_names=["Not At Risk", "At Risk"]))

    print("Confusion matrix (Default threshold = 0.50):")
    cm = confusion_matrix(y_test, preds)
    print(cm)

    auc = roc_auc_score(y_test, probs)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    f1 = f1_score(y_test, preds)

    print(f"\nROC-AUC  : {auc:.3f}")
    print(f"Accuracy : {acc:.3f}")
    print(f"Precision: {prec:.3f}")
    print(f"Recall   : {rec:.3f}")
    print(f"F1-Score : {f1:.3f}")
    print("=" * 40)

    # ---------- Threshold Tuning (prioritize recall >= 85% for screening) ----------
    precisions, recalls, thresholds = precision_recall_curve(y_test, probs)
    target_recall = 0.85
    valid = recalls[:-1] >= target_recall

    calibrated_threshold = 0.5
    calibrated_prec = prec
    calibrated_rec = rec

    if valid.any():
        best_idx = np.argmax(precisions[:-1][valid])
        calibrated_threshold = float(thresholds[valid][best_idx])
        calibrated_prec = float(precisions[:-1][valid][best_idx])
        calibrated_rec = float(recalls[:-1][valid][best_idx])

        tuned_preds = (probs >= calibrated_threshold).astype(int)
        tuned_cm = confusion_matrix(y_test, tuned_preds)

        print(f"\n[THRESHOLD TUNING] Target Recall >= {target_recall:.2f}:")
        print(f"  Suggested threshold: {calibrated_threshold:.3f}")
        print(f"  Precision at threshold: {calibrated_prec:.3f}")
        print(f"  Recall at threshold   : {calibrated_rec:.3f}")
        print("  Confusion matrix at calibrated threshold:")
        print(f"  {tuned_cm}")
        print(f"  (At-risk caught: {tuned_cm[1, 1]} / {tuned_cm[1, 0] + tuned_cm[1, 1]}, missed: {tuned_cm[1, 0]})")

    # ---------- Feature Importance ----------
    importances = pd.Series(model.feature_importances_, index=X_train.columns)
    importances = importances.sort_values(ascending=False)
    print("\nTop 10 risk drivers:")
    for rank, (feat, imp) in enumerate(importances.head(10).items(), 1):
        print(f"  {rank:>2}. {feat:<32} : {imp:.4f} ({imp * 100:.1f}%)")

    # ---------- Save Artifact ----------
    MODEL_2_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_2_PATH)
    print(f"\n[SAVE] Model saved to {MODEL_2_PATH}")
    print("=" * 70 + "\n")

    return model, {
        "auc": auc,
        "accuracy": acc,
        "calibrated_threshold": calibrated_threshold,
        "calibrated_precision": calibrated_prec,
        "calibrated_recall": calibrated_rec,
        "top_features": importances.head(10).to_dict(),
    }


if __name__ == "__main__":
    train_at_risk_model()
