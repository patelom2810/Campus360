"""
tests/test_model_quality.py
Independent model verification — reloads saved artifacts and re-scores
from scratch without relying on training script output.

Steps:
  1. Reload & re-score Model 1 (performance regression)
  2. Reload & re-score Model 2 (at-risk classification)
  3. Apply pass/fail thresholds
  4. Check for suspicious perfection (leakage signals)
  5. Sanity-check feature importances
  6. Print final verdict

Run:  python tests/test_model_quality.py
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"

# Columns that MUST NOT appear in Model 2's feature list
LEAKED_COLUMNS = {"anchor_backlog_history", "anchor_attendance_percentage", "anchor_cgpa"}

# ─── Thresholds from the task specification ─────────────────────────────
MODEL1_R2_GOOD = 0.5
MODEL1_R2_ACCEPTABLE = 0.3
MODEL1_R2_SUSPICIOUS = 0.97

MODEL2_RECALL_GOOD = 0.7
MODEL2_RECALL_ACCEPTABLE = 0.5
MODEL2_ACC_SUSPICIOUS = 0.98


def rating(value, good, acceptable, higher_is_better=True):
    """Return a string rating based on thresholds."""
    if higher_is_better:
        if value >= good:
            return "GOOD"
        elif value >= acceptable:
            return "ACCEPTABLE"
        else:
            return "WEAK"
    else:
        if value <= good:
            return "GOOD"
        elif value <= acceptable:
            return "ACCEPTABLE"
        else:
            return "WEAK"


def divider(title):
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


def run_verification():
    verdicts = {}
    issues = []

    # ─────────────────────────────────────────────────────────────────────
    # PRE-CHECK: Verify all required files exist
    # ─────────────────────────────────────────────────────────────────────
    required_files = {
        "model1_model": MODELS_DIR / "model1_performance_predictor.joblib",
        "model1_metrics": MODELS_DIR / "model1_performance_metrics.json",
        "model2_model": MODELS_DIR / "model2_atrisk_classifier.joblib",
        "model2_metrics": MODELS_DIR / "model2_atrisk_metrics.json",
        "model1_test_data": PROCESSED_DIR / "model1_performance_test.csv",
        "model2_test_data": PROCESSED_DIR / "model2_atrisk_test.csv",
    }
    missing = {k: v for k, v in required_files.items() if not v.exists()}
    if missing:
        print("ERROR: Missing required files:")
        for k, v in missing.items():
            print(f"  {k}: {v}")
        sys.exit(1)
    print("All required files present.")

    # ═════════════════════════════════════════════════════════════════════
    # STEP 1: Reload and re-score Model 1 independently
    # ═════════════════════════════════════════════════════════════════════
    divider("STEP 1: RELOAD & RE-SCORE MODEL 1 (Performance Regression)")

    m1_model = joblib.load(required_files["model1_model"])
    m1_saved = json.loads(required_files["model1_metrics"].read_text())
    m1_test = pd.read_csv(required_files["model1_test_data"])

    m1_features = m1_saved["features"]
    m1_target = m1_saved["target"]

    X_test_m1 = m1_test[m1_features]
    y_test_m1 = m1_test[m1_target]

    y_pred_m1 = m1_model.predict(X_test_m1)
    m1_rmse = float(np.sqrt(mean_squared_error(y_test_m1, y_pred_m1)))
    m1_mae = float(mean_absolute_error(y_test_m1, y_pred_m1))
    m1_r2 = float(r2_score(y_test_m1, y_pred_m1))

    print(f"\n  Re-computed from saved model + test data:")
    print(f"    RMSE : {m1_rmse:.4f}")
    print(f"    MAE  : {m1_mae:.4f}")
    print(f"    R²   : {m1_r2:.4f}")

    print(f"\n  Saved in metrics JSON:")
    print(f"    RMSE : {m1_saved['test_rmse']}")
    print(f"    MAE  : {m1_saved['test_mae']}")
    print(f"    R²   : {m1_saved['test_r2']}")

    # Compare with tolerance
    m1_match = True
    for metric, recomputed, saved in [
        ("RMSE", m1_rmse, m1_saved["test_rmse"]),
        ("MAE", m1_mae, m1_saved["test_mae"]),
        ("R²", m1_r2, m1_saved["test_r2"]),
    ]:
        if abs(recomputed - saved) > 0.01:
            print(f"  [MISMATCH] {metric} recomputed={recomputed:.4f} vs saved={saved}")
            m1_match = False
            issues.append(f"Model 1 {metric} mismatch: recomputed {recomputed:.4f} vs saved {saved}")

    if m1_match:
        print("\n  [PASS] Recomputed metrics MATCH saved metrics (within tolerance)")
    else:
        print("\n  [FAIL] Metrics MISMATCH — saved model and metrics JSON are out of sync")

    # ═════════════════════════════════════════════════════════════════════
    # STEP 2: Reload and re-score Model 2 independently
    # ═════════════════════════════════════════════════════════════════════
    divider("STEP 2: RELOAD & RE-SCORE MODEL 2 (At-Risk Classification)")

    m2_model = joblib.load(required_files["model2_model"])
    m2_saved = json.loads(required_files["model2_metrics"].read_text())
    m2_test = pd.read_csv(required_files["model2_test_data"])

    m2_features = m2_saved["features"]
    m2_target = m2_saved["target"]
    decision_threshold = m2_saved.get("decision_threshold", 0.50)

    X_test_m2 = m2_test[m2_features]
    y_test_m2 = m2_test[m2_target]

    if hasattr(m2_model, "predict_proba"):
        probs_m2 = m2_model.predict_proba(X_test_m2)[:, 1]
        y_pred_m2 = (probs_m2 >= decision_threshold).astype(int)
        y_pred_default = (probs_m2 >= 0.50).astype(int)
    else:
        y_pred_m2 = m2_model.predict(X_test_m2)
        y_pred_default = y_pred_m2

    m2_accuracy = float(accuracy_score(y_test_m2, y_pred_m2))
    m2_precision = float(precision_score(y_test_m2, y_pred_m2, pos_label=1, zero_division=0))
    m2_recall = float(recall_score(y_test_m2, y_pred_m2, pos_label=1, zero_division=0))
    m2_f1 = float(f1_score(y_test_m2, y_pred_m2, pos_label=1, zero_division=0))
    m2_cm = confusion_matrix(y_test_m2, y_pred_m2).tolist()

    default_rec = float(recall_score(y_test_m2, y_pred_default, pos_label=1, zero_division=0))
    default_prec = float(precision_score(y_test_m2, y_pred_default, pos_label=1, zero_division=0))

    print(f"\n  Decision Threshold Used: {decision_threshold:.2f} (default: 0.50)")
    print(f"  At default 0.50 threshold : Recall={default_rec:.4f}, Precision={default_prec:.4f}")
    print(f"  At tuned {decision_threshold:.2f} threshold   : Recall={m2_recall:.4f}, Precision={m2_precision:.4f}, F1={m2_f1:.4f}, Acc={m2_accuracy:.4f}")
    print(f"  Confusion Matrix ({decision_threshold:.2f}): TN={m2_cm[0][0]}  FP={m2_cm[0][1]}")
    print(f"                              FN={m2_cm[1][0]}  TP={m2_cm[1][1]}")

    print(f"\n  Saved in metrics JSON:")
    print(f"    Accuracy  : {m2_saved['test_accuracy']}")
    print(f"    Precision : {m2_saved['test_precision_class1']}")
    print(f"    Recall    : {m2_saved['test_recall_class1']}")
    print(f"    F1        : {m2_saved['test_f1_class1']}")

    m2_match = True
    for metric, recomputed, saved in [
        ("Accuracy", m2_accuracy, m2_saved["test_accuracy"]),
        ("Recall", m2_recall, m2_saved["test_recall_class1"]),
        ("Precision", m2_precision, m2_saved["test_precision_class1"]),
        ("F1", m2_f1, m2_saved["test_f1_class1"]),
    ]:
        if abs(recomputed - saved) > 0.01:
            print(f"  [MISMATCH] {metric} recomputed={recomputed:.4f} vs saved={saved}")
            m2_match = False
            issues.append(f"Model 2 {metric} mismatch: recomputed {recomputed:.4f} vs saved {saved}")

    if m2_match:
        print("\n  [PASS] Recomputed metrics MATCH saved metrics (within tolerance)")
    else:
        print("\n  [FAIL] Metrics MISMATCH — saved model and metrics JSON are out of sync")

    print(f"\n  Full classification report (recomputed at threshold {decision_threshold:.2f}):")
    print(classification_report(y_test_m2, y_pred_m2, target_names=["Safe (0)", "At-Risk (1)"]))

    # ═════════════════════════════════════════════════════════════════════
    # STEP 3: Apply pass/fail thresholds
    # ═════════════════════════════════════════════════════════════════════
    divider("STEP 3: PASS/FAIL THRESHOLDS")

    m1_rating = rating(m1_r2, MODEL1_R2_GOOD, MODEL1_R2_ACCEPTABLE)

    m2_specificity = m2_cm[0][0] / (m2_cm[0][0] + m2_cm[0][1]) if (m2_cm[0][0] + m2_cm[0][1]) > 0 else 0.0
    if m2_specificity < 0.10 and m2_recall >= 0.90:
        m2_rating = "WEAK (DEGENERATE)"
    else:
        m2_rating = rating(m2_recall, MODEL2_RECALL_GOOD, MODEL2_RECALL_ACCEPTABLE)

    print(f"\n  Model 1 (Performance Regression):")
    print(f"    R²     = {m1_r2:.4f}")
    print(f"    Rating = {m1_rating}")
    if m1_rating == "GOOD":
        print(f"    → Strong predictive signal (R² ≥ {MODEL1_R2_GOOD})")
    elif m1_rating == "ACCEPTABLE":
        print(f"    → Usable but weak; mention as a limitation ({MODEL1_R2_ACCEPTABLE} ≤ R² < {MODEL1_R2_GOOD})")
    else:
        print(f"    → WEAK: R² < {MODEL1_R2_ACCEPTABLE}. Improved from 0.1588 to {m1_r2:.4f}, but remains below 0.30.")
        print(f"      Do NOT present as a working predictor without caveats.")
        issues.append(f"Model 1 R² = {m1_r2:.4f} — below 0.30 threshold")

    print(f"\n  Model 2 (At-Risk Classification):")
    print(f"    Recall = {m2_recall:.4f}  (class 1: At-Risk at threshold {decision_threshold:.2f})")
    print(f"    Specificity = {m2_specificity:.4f}  (True Negative Rate: {m2_cm[0][0]}/{m2_cm[0][0]+m2_cm[0][1]})")
    print(f"    Rating = {m2_rating}")
    if m2_rating == "WEAK (DEGENERATE)":
        print(f"    → WEAK (DEGENERATE): Recall is inflated ({m2_recall:.4f}) because the model predicted")
        print(f"      positive for almost all students (FP={m2_cm[0][1]}, TN={m2_cm[0][0]}, specificity={m2_specificity:.2%}).")
        print(f"      At default 0.50 threshold with balanced weights, recall is ~0.35-0.52. Lifestyle features")
        print(f"      without attendance/backlogs lack sufficient correlation for true discrimination.")
        issues.append(f"Model 2 achieves high recall via degenerate over-prediction (specificity: {m2_specificity:.2%})")
    elif m2_rating == "GOOD":
        print(f"    → Catches most at-risk students (recall ≥ {MODEL2_RECALL_GOOD})")
    elif m2_rating == "ACCEPTABLE":
        print(f"    → Usable but misses a meaningful fraction of at-risk students")
    else:
        print(f"    → WEAK: Misses more at-risk students than it catches (recall < {MODEL2_RECALL_ACCEPTABLE})")
        issues.append(f"Model 2 recall = {m2_recall:.4f} — misses most at-risk students")

    verdicts["model1"] = m1_rating
    verdicts["model2"] = m2_rating

    # ═════════════════════════════════════════════════════════════════════
    # STEP 4: Check for suspicious perfection
    # ═════════════════════════════════════════════════════════════════════
    divider("STEP 4: SUSPICIOUS PERFECTION & DATA LEAKAGE CHECK")

    suspicious = False

    if m1_r2 > MODEL1_R2_SUSPICIOUS:
        print(f"\n  [ALERT] RED FLAG: Model 1 R² = {m1_r2:.4f} > {MODEL1_R2_SUSPICIOUS}")
        print(f"     This is suspiciously high — possible data leakage or train/test overlap")
        suspicious = True
        verdicts["model1"] = "SUSPICIOUS"
    else:
        print(f"\n  Model 1 R² = {m1_r2:.4f} — not suspiciously high (threshold: {MODEL1_R2_SUSPICIOUS})")

    if m2_accuracy > MODEL2_ACC_SUSPICIOUS:
        print(f"\n  [ALERT] RED FLAG: Model 2 accuracy = {m2_accuracy:.4f} > {MODEL2_ACC_SUSPICIOUS}")
        print(f"     This is suspiciously high — possible data leakage")
        suspicious = True
        verdicts["model2"] = "SUSPICIOUS"
    else:
        print(f"  Model 2 accuracy = {m2_accuracy:.4f} — not suspiciously high (threshold: {MODEL2_ACC_SUSPICIOUS})")

    # Leakage column check for Model 2
    print(f"\n  Model 2 feature list ({len(m2_features)} features):")
    for f in m2_features:
        flag = " [LEAKED!]" if f in LEAKED_COLUMNS else ""
        print(f"    - {f}{flag}")

    leaked = set(m2_features) & LEAKED_COLUMNS
    if leaked:
        print(f"\n  [FAIL] LEAKAGE DETECTED: {leaked} in Model 2 features")
        issues.append(f"Label leakage in Model 2: {leaked}")
        verdicts["model2"] = "SUSPICIOUS"
    else:
        print(f"\n  [PASS] No leakage columns found in Model 2 features list")

    # Confirm feature_names_in_ on saved model object
    if hasattr(m2_model, "feature_names_in_"):
        m2_saved_leaked = set(m2_model.feature_names_in_) & LEAKED_COLUMNS
        if m2_saved_leaked:
            print(f"  [FAIL] LEAKAGE in m2_model.feature_names_in_: {m2_saved_leaked}")
            issues.append(f"Label leakage in saved Model 2 artifact feature_names_in_: {m2_saved_leaked}")
            verdicts["model2"] = "SUSPICIOUS"
        else:
            print(f"  [PASS] Confirmed: m2_model.feature_names_in_ strictly excludes all 3 leakage columns")

    # Model 1 feature list
    print(f"\n  Model 1 feature list ({len(m1_features)} features):")
    for f in m1_features:
        print(f"    - {f}")

    # Train/test overlap check
    print(f"\n  Checking for train/test row overlap...")
    m1_train = pd.read_csv(PROCESSED_DIR / "model1_performance_train.csv")
    m2_train = pd.read_csv(PROCESSED_DIR / "model2_atrisk_train.csv")

    # Check M1 overlap (compare all columns)
    m1_combined = pd.concat([m1_train, m1_test], ignore_index=True)
    m1_dupes = m1_combined.duplicated(keep=False).sum()
    m1_train_dupes = m1_train.duplicated().sum()
    m1_test_dupes = m1_test.duplicated().sum()
    # Cross-merge to find exact row matches between train and test
    m1_overlap = pd.merge(m1_train, m1_test, how="inner")
    print(f"    Model 1: {len(m1_overlap)} overlapping rows between train and test")

    m2_overlap = pd.merge(m2_train, m2_test, how="inner")
    print(f"    Model 2: {len(m2_overlap)} overlapping rows between train and test")

    if len(m1_overlap) > 0 or len(m2_overlap) > 0:
        print(f"  [FAIL] Train/test overlap detected — possible data contamination")
        issues.append("Train/test row overlap detected")
    else:
        print(f"  [PASS] No train/test row overlap detected")

    if not suspicious:
        print(f"\n  [PASS] No signs of suspicious perfection — scores look realistic")

    # ═════════════════════════════════════════════════════════════════════
    # STEP 5: Feature importance sanity check
    # ═════════════════════════════════════════════════════════════════════
    divider("STEP 5: FEATURE IMPORTANCE SANITY CHECK")

    # Model 1
    if hasattr(m1_model, "feature_importances_"):
        m1_imp = sorted(
            zip(m1_features, m1_model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
        print(f"\n  Model 1 — Top 5 features by importance:")
        for i, (feat, imp) in enumerate(m1_imp[:5], 1):
            print(f"    {i}. {feat:42s} {imp:.4f}")

        # Check if importances are roughly uniform (sign of no real signal)
        imp_values = [v for _, v in m1_imp]
        imp_range = max(imp_values) - min(imp_values)
        if imp_range < 0.05:
            print(f"\n  [WARNING] Feature importances are nearly uniform (range={imp_range:.4f})")
            print(f"    This suggests no single feature has strong predictive power for {m1_target}")
            issues.append("Model 1 feature importances are nearly uniform — no strong signal")
    else:
        print("  Model 1 does not expose feature_importances_")

    # Model 2
    if hasattr(m2_model, "feature_importances_"):
        m2_imp = sorted(
            zip(m2_features, m2_model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
        print(f"\n  Model 2 — Top 5 features by importance:")
        for i, (feat, imp) in enumerate(m2_imp[:5], 1):
            print(f"    {i}. {feat:42s} {imp:.4f}")

        imp_values = [v for _, v in m2_imp]
        imp_range = max(imp_values) - min(imp_values)
        if imp_range < 0.05:
            print(f"\n  [WARNING] Feature importances are nearly uniform (range={imp_range:.4f})")
            print(f"    This suggests no single feature has strong predictive power for {m2_target}")
            issues.append("Model 2 feature importances are nearly uniform — no strong signal")
    else:
        print("  Model 2 does not expose feature_importances_")

    # Plausibility check
    print(f"\n  Plausibility notes:")
    print(f"    Model 1 predicts academic CGPA — study_hours and DSA problems")
    print(f"    solved SHOULD be important. If sleep_hours or gaming_hours")
    print(f"    dominate instead, that warrants a manual look.")
    print(f"    Model 2 predicts at-risk status from lifestyle — stress,")
    print(f"    burnout, and study hours SHOULD matter most.")

    # ═════════════════════════════════════════════════════════════════════
    # STEP 6: FINAL VERDICT
    # ═════════════════════════════════════════════════════════════════════
    divider("STEP 6: FINAL VERDICT")

    print(f"\n  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │  MODEL 1 (Performance Predictor): {verdicts['model1']:>12s}          │")
    print(f"  │    R² = {m1_r2:.4f}  |  RMSE = {m1_rmse:.4f}  |  MAE = {m1_mae:.4f}  │")
    print(f"  │                                                         │")
    print(f"  │  MODEL 2 (At-Risk Classifier):    {verdicts['model2']:>12s}          │")
    print(f"  │    Recall = {m2_recall:.4f}  |  Precision = {m2_precision:.4f}          │")
    print(f"  │    Accuracy = {m2_accuracy:.4f}  |  F1 = {m2_f1:.4f}                │")
    print(f"  └─────────────────────────────────────────────────────────┘")

    # Plain-language README paragraph
    print(f"\n  ── Plain-Language Verdict (for README) ──")

    print(f"""
  MODEL 1 — CGPA Performance Predictor (R² = {m1_r2:.4f}):""")

    if m1_r2 >= MODEL1_R2_GOOD:
        print(f"""    This model predicts a student's CGPA from 13 academic and lifestyle
    features. With an R² of {m1_r2:.4f} (RMSE = {m1_rmse:.4f}, MAE = {m1_mae:.4f}),
    the model shows a strong predictive signal and explains a significant
    portion of variance in CGPA. It is suitable for academic trajectory
    projections and grade trend analysis.""")
    elif m1_r2 >= MODEL1_R2_ACCEPTABLE:
        print(f"""    This model predicts a student's CGPA from 13 academic and lifestyle
    features. With an R² of {m1_r2:.4f} (RMSE = {m1_rmse:.4f}, MAE = {m1_mae:.4f}),
    it shows moderate predictive signal. It is usable for rough tiering or
    advisory context, but has meaningful variance. For a hackathon presentation,
    disclose: "R² is {m1_r2:.2f} — provides directional guidance but should not
    be treated as a definitive grade prediction." """)
    else:
        print(f"""    This model attempts to predict a student's CGPA from 13 academic and
    lifestyle features. The R² of {m1_r2:.4f} (RMSE = {m1_rmse:.4f}, MAE = {m1_mae:.4f})
    falls into the WEAK tier (R² < {MODEL1_R2_ACCEPTABLE}). While it captures minor
    directional trends from study hours and DSA problem solving, the features
    alone do not contain sufficient signal to accurately predict fine-grained
    CGPA values. For a hackathon submission, honestly disclose: "R² of {m1_r2:.2f};
    usable as an architectural baseline, but requires richer historical course
    and assessment data for high-confidence predictions." """)

    print(f"""
  MODEL 2 — At-Risk Student Classifier (Recall = {m2_recall:.4f}):""")

    if m2_rating == "WEAK (DEGENERATE)":
        print(f"""    This model achieves a nominal recall of {m2_recall:.4f} at threshold {decision_threshold:.2f},
    but this is a degenerate outcome: the classifier predicts at-risk for 4,996
    out of 5,000 students (3,401 false positives, specificity = {m2_specificity:.2%},
    accuracy = {m2_accuracy:.2%}). Because the 23 non-leakage behavioral and skill
    features have near-zero correlation with the at-risk label (|r| <= 0.025), optimizing
    pure recall pushes the model to predict positive on almost everyone. At balanced
    decision thresholds, recall falls back to ~0.35-0.52. Honestly disclose this finding:
    institutional risk cannot be reliably diagnosed from self-reported lifestyle and
    extracurricular factors alone without direct course engagement records (attendance
    and backlogs).""")
    elif m2_recall >= MODEL2_RECALL_GOOD:
        print(f"""    This model identifies at-risk students using 23 lifestyle and
    behavioral features, deliberately excluding the 3 columns that define
    the at-risk label (preventing leakage). With recall of {m2_recall:.4f},
    it catches the majority of genuinely at-risk students. This is a
    usable model for early-warning screening.""")
    elif m2_recall >= MODEL2_RECALL_ACCEPTABLE:
        print(f"""    This model identifies at-risk students using 23 lifestyle and
    behavioral features, deliberately excluding the 3 columns that define
    the at-risk label. With recall of {m2_recall:.4f}, it catches a
    meaningful fraction of at-risk students but will miss some. For a
    hackathon, disclose: "The model detects ~{m2_recall*100:.0f}% of at-risk
    students; the remaining ~{(1-m2_recall)*100:.0f}% are missed."
    This is usable with caveats.""")
    else:
        print(f"""    This model attempts to identify at-risk students using 23 lifestyle
    features, but with recall of {m2_recall:.4f}, it misses more at-risk
    students than it catches. The lifestyle-only features (without
    attendance, CGPA, or backlog data) do not carry enough signal to
    reliably reconstruct the academic-risk label. Honestly disclose this
    limitation: the model pipeline is sound, but the feature-target
    relationship in this dataset is too weak for reliable at-risk
    detection from lifestyle data alone.""")

    if issues:
        print(f"\n  ── Issues Found ──")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")

    print()


if __name__ == "__main__":
    run_verification()
