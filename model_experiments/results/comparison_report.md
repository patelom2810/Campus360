# Campus360 ML Model Comparison Report

> **Notice**: This benchmark was conducted in complete isolation from production. No production models, schemas, or live API endpoints were modified.

## Executive Summary

This evaluation benchmarks 13 candidate regression models for **Model 1 (CGPA Predictor)** and 12 candidate classification models for **Model 2 (At-Risk Student Classifier)** on the identical train/test splits (80/20, `random_state=42`). Both tasks adhere strictly to production feature engineering constraints and label-leakage boundaries.

### Key Takeaways
- **Model 1 (Regression, target: `anchor_cgpa`)**: Current production model (`Gradient Boosting`) achieves $R^2 = 0.2096$ (RMSE: 0.7581). The top benchmark algorithm is `Linear Regression` with $R^2 = 0.2183$ (Δ = +0.0087).
- **Model 2 (Classification, target: `at_risk_flag`)**: Current production model (`Random Forest`) achieves Recall = 0.4865, AUC = 0.5058, F1 = 0.3867. The top valid candidate on Recall is `Logistic Regression` with Recall = 0.4991 (Δ = +0.0126) and AUC = 0.5190.

---

## Model 1 Comparison: Performance Predictor (anchor_cgpa)

Evaluated on 28 features (13 original anchor + 11 expanded anchor + 4 interaction features). Scalers applied only to distance, linear, and neural network algorithms; tree models evaluated on native feature matrices.

**Ranked by $R^2$ (Descending)**:

| Rank | Algorithm | Production Status | $R^2$ | RMSE | MAE | Status Flag |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| 1 | Linear Regression | Candidate | 0.2183 | 0.7539 | 0.5987 | Nominal |
| 2 | Ridge | Candidate | 0.2183 | 0.7539 | 0.5987 | Nominal |
| 3 | ElasticNet | Candidate | 0.2172 | 0.7544 | 0.5992 | Nominal |
| 4 | Lasso | Candidate | 0.2161 | 0.7550 | 0.5996 | Nominal |
| 5 | XGBoost | Candidate | 0.2133 | 0.7563 | 0.6015 | Nominal |
| 6 | LightGBM | Candidate | 0.2122 | 0.7569 | 0.6018 | Nominal |
| 7 | **Gradient Boosting** | **CURRENT PRODUCTION** | 0.2096 | 0.7581 | 0.6022 | Nominal |
| 8 | Extra Trees | Candidate | 0.2027 | 0.7614 | 0.6050 | Nominal |
| 9 | Random Forest | Candidate | 0.1979 | 0.7637 | 0.6065 | Nominal |
| 10 | AdaBoost | Candidate | 0.1605 | 0.7813 | 0.6216 | Nominal |
| 11 | SVR (RBF) | Candidate | 0.1574 | 0.7827 | 0.6193 | Nominal |
| 12 | KNN Regressor | Candidate | 0.0857 | 0.8154 | 0.6489 | Nominal |
| 13 | MLP Regressor | Candidate | 0.0323 | 0.8388 | 0.6607 | Nominal |

### Model 1 Recommendation

**Recommendation: Retain Current Production Model (Gradient Boosting).** While `Linear Regression` nominally achieved the highest $R^2$ (0.2183 vs 0.2096), the difference of only +0.0087 $R^2$ points (0.87%) is within statistical margin of error and represents random split variance rather than a genuine architectural advantage. Swapping models would introduce deployment risk without meaningful predictive gain.

---

## Model 2 Comparison: At-Risk Classifier (at_risk_flag)

Evaluated on 23 non-leakage lifestyle and skill features. Label-defining academic records (`anchor_backlog_history`, `anchor_attendance_percentage`, `anchor_cgpa`) are strictly excluded. Balanced class weights or equivalent priors were enforced wherever supported.

**Ranked by Recall (Descending)** (cost-asymmetric safety priority: missing an at-risk student costs more than a false intervention):

| Rank | Algorithm | Production Status | Recall | ROC AUC | Precision | F1 | Accuracy | TN | FP | FN | TP | Safety Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | Logistic Regression | Candidate | 0.4991 | 0.5190 | 0.3333 | 0.3997 | 0.5218 | 1,813 | 1,592 | 799 | 796 | Nominal |
| 2 | LightGBM | Candidate | 0.4878 | 0.5056 | 0.3277 | 0.3920 | 0.5174 | 1,809 | 1,596 | 817 | 778 | Nominal |
| 3 | SVM (RBF) | Candidate | 0.4871 | 0.5110 | 0.3321 | 0.3949 | 0.5238 | 1,842 | 1,563 | 818 | 777 | Nominal |
| 4 | **Random Forest** | **CURRENT PRODUCTION** | 0.4865 | 0.5058 | 0.3209 | 0.3867 | 0.5078 | 1,763 | 1,642 | 819 | 776 | Nominal |
| 5 | Extra Trees | Candidate | 0.4708 | 0.5131 | 0.3265 | 0.3856 | 0.5214 | 1,856 | 1,549 | 844 | 751 | Nominal |
| 6 | XGBoost | Candidate | 0.4495 | 0.5014 | 0.3147 | 0.3703 | 0.5122 | 1,844 | 1,561 | 878 | 717 | Nominal |
| 7 | MLP Classifier | Candidate | 0.2345 | 0.5076 | 0.3366 | 0.2764 | 0.6084 | 2,668 | 737 | 1,221 | 374 | Nominal |
| 8 | KNN Classifier | Candidate | 0.1367 | 0.4987 | 0.3234 | 0.1922 | 0.6334 | 2,949 | 456 | 1,377 | 218 | Nominal |
| 9 | QDA | Candidate | 0.0019 | 0.5214 | 0.3000 | 0.0037 | 0.6802 | 3,398 | 7 | 1,592 | 3 | 🚨 DEGENERATE |
| 10 | Naive Bayes | Candidate | 0.0000 | 0.5100 | 0.0000 | 0.0000 | 0.6810 | 3,405 | 0 | 1,595 | 0 | 🚨 DEGENERATE |
| 11 | AdaBoost | Candidate | 0.0000 | 0.5054 | 0.0000 | 0.0000 | 0.6810 | 3,405 | 0 | 1,595 | 0 | 🚨 DEGENERATE |
| 12 | Gradient Boosting | Candidate | 0.0000 | 0.5038 | 0.0000 | 0.0000 | 0.6804 | 3,402 | 3 | 1,595 | 0 | 🚨 DEGENERATE |

### Model 2 Recommendation

**Recommendation: Retain Current Production Model (Random Forest).** `Logistic Regression` achieved Recall = 0.4991 compared to 0.4865 for Random Forest (Δ = +0.0126), but its ROC AUC (0.5190) and precision (0.3333) indicate negligible practical divergence. Given the cost of swapping production artifacts and retraining pipelines, this minor difference does not justify modifying the live service.

---

## Safety Checks, Degeneracy Audits & Data Integrity

### 1. Leakage Prevention Assertion
- **Enforced Rule**: `MODEL_2_FEATURES ∩ {anchor_backlog_history, anchor_attendance_percentage, anchor_cgpa} == ∅`.
- **Audit Result**: PASSED. All 23 Model 2 features were verified programmatically prior to model fitting. Zero target-defining features entered the training pipeline.

### 2. Degeneracy & Suspicious Metric Callouts
#### Degenerate Classifiers (Recall < 0.05 or > 0.95)
- **Naive Bayes** (Recall: `0.0000`, Precision: `0.0000`, TP: `0`, FN: `1595`): Flagged as **DEGENERATE**. The algorithm collapsed into trivial majority or minority predictions, failing to capture the minority at-risk cohort. Disqualified from consideration as a viable production model regardless of overall accuracy.
- **QDA** (Recall: `0.0019`, Precision: `0.3000`, TP: `3`, FN: `1592`): Flagged as **DEGENERATE**. The algorithm collapsed into trivial majority or minority predictions, failing to capture the minority at-risk cohort. Disqualified from consideration as a viable production model regardless of overall accuracy.
- **AdaBoost** (Recall: `0.0000`, Precision: `0.0000`, TP: `0`, FN: `1595`): Flagged as **DEGENERATE**. The algorithm collapsed into trivial majority or minority predictions, failing to capture the minority at-risk cohort. Disqualified from consideration as a viable production model regardless of overall accuracy.
- **Gradient Boosting** (Recall: `0.0000`, Precision: `0.0000`, TP: `0`, FN: `1595`): Flagged as **DEGENERATE**. The algorithm collapsed into trivial majority or minority predictions, failing to capture the minority at-risk cohort. Disqualified from consideration as a viable production model regardless of overall accuracy.

### 3. Missing Value Imputation Log
- All features across the entire 25,000-record dataset were complete. No median imputations were necessary.

---

## Reproduction Instructions

To reproduce these benchmarks without altering production code:
```bash
# 1. Ensure isolated virtual environment dependencies are installed
pip install -r model_experiments/requirements-experiments.txt

# 2. Execute the comparison harness
python model_experiments/run_comparison.py
```

*Report generated automatically by Campus360 ML Comparison Harness.*
