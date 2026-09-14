# Current Production Model Status & Ground Truth Audit

> **Definitive Status Report**: This report supersedes all prior documentation, benchmarks, and model swap summaries. Every metric, hyperparameter, and feature list in this document was independently inspected, re-scored live from raw test datasets, and cross-verified against production artifacts on September 14, 2026.

---

## Model 1: Performance Prediction

- **Algorithm**: `GradientBoostingRegressor`
- **Hyperparameters**:
  ```python
  {
      'alpha': 0.9,
      'ccp_alpha': 0.0,
      'criterion': 'deprecated',
      'init': None,
      'learning_rate': 0.05,
      'loss': 'squared_error',
      'max_depth': 3,
      'max_features': 'sqrt',
      'max_leaf_nodes': None,
      'min_impurity_decrease': 0.0,
      'min_samples_leaf': 5,
      'min_samples_split': 2,
      'min_weight_fraction_leaf': 0.0,
      'n_estimators': 200,
      'n_iter_no_change': None,
      'random_state': 42,
      'subsample': 1.0,
      'tol': 0.0001,
      'validation_fraction': 0.1,
      'verbose': 0,
      'warm_start': False
  }
  ```
- **Target**: `anchor_cgpa` (continuous float on a 5.0–10.0 scale)
  - *Description*: Model 1 predicts continuous student semester GPA (`anchor_cgpa`) from daily study habits, attendance, and technical milestones to forecast directional academic trajectory.
- **Features**: 28 total (24 primary attributes + 4 engineered interaction terms) —
  1. `anchor_attendance_percentage`
  2. `anchor_study_hours_daily`
  3. `anchor_self_learning_hours`
  4. `anchor_sleep_hours`
  5. `anchor_screen_time`
  6. `anchor_gaming_hours`
  7. `anchor_stress_level`
  8. `anchor_burnout_score`
  9. `anchor_backlog_history`
  10. `anchor_dsa_problems_solved`
  11. `anchor_internships_completed`
  12. `anchor_motivation_level`
  13. `anchor_family_income_lpa`
  14. `anchor_resume_score`
  15. `anchor_communication_skills`
  16. `anchor_aptitude_score`
  17. `anchor_mock_interview_score`
  18. `anchor_hackathons_participated`
  19. `anchor_development_projects_count`
  20. `anchor_ai_ml_projects`
  21. `anchor_git_hub_repos`
  22. `anchor_ai_tool_usage_frequency`
  23. `anchor_prompt_engineering_skill`
  24. `anchor_adaptability_score`
  25. `effort_score`
  26. `screen_to_study_ratio`
  27. `wellness_score`
  28. `project_activity`
- **Live re-scored metrics**:
  - **RMSE**: `0.7581` (raw: `0.7580990833717749`)
  - **MAE**: `0.6022` (raw: `0.6022440764535141`)
  - **R²**: `0.2096` (raw: `0.20958244012411187`)
  - *Comparison with `models/model1_performance_metrics.json`*: Exact match across all metrics (`test_rmse: 0.7581`, `test_mae: 0.6022`, `test_r2: 0.2096`).
- **Used by**:
  - `POST /api/models/predict-performance` (Direct scenario simulation slider endpoint via `model1.predict()`)
  - `POST /api/assess/new-student` (Single-student intake via `run_full_assessment()`)
  - `POST /api/assess/csv-match` (Batch CSV upload matching preview via `run_batch_assessment()`)
  - `POST /api/assess/csv-match/confirm` (Batch CSV execution via `run_batch_assessment()`)
  - `POST /api/assess/csv-stitch` (CSV cohort assessment via `run_full_assessment()`)
  - `POST /api/assess/chat-guided` (Conversational student evaluation via `run_full_assessment()`)
- **Verdict**: **Weak** (per established thresholds: $R^2 \ge 0.5$ good, $0.3 \le R^2 < 0.5$ acceptable, $R^2 < 0.3$ weak). With $R^2 = 0.2096$, the model accounts for ~21% of variance in student GPA; it is intentionally positioned and labeled throughout the system as a directional guidance indicator rather than an exact grade forecasting tool.

---

## Model 2: At-Risk Detection

- **Algorithm**: `LogisticRegression`
- **Hyperparameters**:
  ```python
  {
      'C': 1.0,
      'class_weight': 'balanced',
      'dual': False,
      'fit_intercept': True,
      'intercept_scaling': 1,
      'l1_ratio': 0.0,
      'max_iter': 2000,
      'n_jobs': None,
      'penalty': 'l2',
      'random_state': 42,
      'solver': 'liblinear',
      'tol': 0.0001,
      'verbose': 0,
      'warm_start': False
  }
  ```
- **Target**: `at_risk_flag` = `1 if (anchor_backlog_history >= 1 or anchor_attendance_percentage < 55 or anchor_cgpa < 5.5) else 0`
  - *Description*: Model 2 predicts binary academic vulnerability (`at_risk_flag`) using strictly non-academic lifestyle, psychological, and behavioral attributes to enable preventative faculty triage before formal disciplinary or academic failure occurs.
- **Features**: 23 total (21 primary lifestyle/behavioral attributes + 2 engineered interaction terms) —
  1. `anchor_sleep_hours`
  2. `anchor_screen_time`
  3. `anchor_gaming_hours`
  4. `anchor_stress_level`
  5. `anchor_burnout_score`
  6. `anchor_study_hours_daily`
  7. `anchor_self_learning_hours`
  8. `anchor_motivation_level`
  9. `anchor_adaptability_score`
  10. `anchor_gym_frequency`
  11. `anchor_family_income_lpa`
  12. `anchor_resume_score`
  13. `anchor_communication_skills`
  14. `anchor_aptitude_score`
  15. `anchor_mock_interview_score`
  16. `anchor_hackathons_participated`
  17. `anchor_development_projects_count`
  18. `anchor_ai_ml_projects`
  19. `anchor_git_hub_repos`
  20. `anchor_ai_tool_usage_frequency`
  21. `anchor_prompt_engineering_skill`
  22. `wellness_score`
  23. `screen_to_study_ratio`
- **Excluded (anti-leakage)**:
  - Confirmed absent: `anchor_backlog_history` (Present in feature list? **False**)
  - Confirmed absent: `anchor_attendance_percentage` (Present in feature list? **False**)
  - Confirmed absent: `anchor_cgpa` (Present in feature list? **False**)
- **Live re-scored metrics**:
  - **ROC AUC**: `0.5190` (raw: `0.518970166498649`)
  - **Accuracy**: `0.5226` (raw: `0.5226`)
  - **Precision**: `0.3346` (raw: `0.33458646616541354`)
  - **Recall**: `0.5022` (raw: `0.5021943573667712`)
  - **F1**: `0.4016` (raw: `0.4016044121333668`)
  - **Confusion Matrix**: `[[1812, 1593], [794, 801]]` (TN=1812, FP=1593, FN=794, TP=801 across 5,000 test cohort rows)
  - *Comparison with `models/model2_atrisk_metrics.json`*: Exact match across all metrics (`roc_auc: 0.519`, `test_accuracy: 0.5226`, `test_precision_class1: 0.3346`, `test_recall_class1: 0.5022`, `test_f1_class1: 0.4016`, `confusion_matrix: [[1812, 1593], [794, 801]]`).
- **Used by**:
  - `GET /api/students/{student_id}` (Queries `get_at_risk_students_cache()` running `model2.predict_proba()`)
  - `GET /api/analytics/at-risk-students` (Queries `get_at_risk_students_cache()` running `model2.predict_proba()`)
  - `GET /api/analytics/atrisk-table` (Queries `get_at_risk_students_cache()` running `model2.predict_proba()`)
  - `GET /api/models/atrisk-metadata` (Exposes production model parameters, threshold, and metrics from `get_model2()`)
  - `POST /api/assess/new-student` (Single-student intake via `run_full_assessment()`)
  - `POST /api/assess/csv-match` (Batch CSV upload matching preview via `run_batch_assessment()`)
  - `POST /api/assess/csv-match/confirm` (Batch CSV execution via `run_batch_assessment()`)
  - `POST /api/assess/csv-stitch` (CSV cohort assessment via `run_full_assessment()`)
  - `POST /api/assess/chat-guided` (Conversational student evaluation via `run_full_assessment()`)
- **Verdict**: **Acceptable** (per established thresholds: $\text{Recall} \ge 0.7$ good, $0.5 \le \text{Recall} < 0.7$ acceptable, $\text{Recall} < 0.5$ weak). With Recall = $0.5022$, Model 2 catches $50.22\%$ (801 of 1,595) of genuinely at-risk students from lifestyle indicators alone without circular leakage; transparently operated as an exploratory screening filter with disclosed $33.46\%$ precision (~2 in 3 flags are false alarms).

---

## Career Readiness Engine (not ML)

- **Type**: Rule-based weighted composite, not a trained machine learning model.
- **Implementation**: Computes a deterministic readiness score (0–100 scale) with branch-aware penalties, credential bonuses, and tier adjustments directly in `src/api/assessment_engine.py` (`_compute_career_readiness`).
- **Stub Confirmation**: `src/models/train_career_model.py` is confirmed as an intentional empty stub with a verified file size of **0 bytes**.

---

## GenAI Insights Layer: Google Gemini

- **Production Foundation Model**: `gemini-3.5-flash-lite`
- **Architectural Role**: Purely explanatory and synthesis layer. Operates downstream of Scikit-Learn predictions and Star-Schema SQL queries to produce faculty intervention briefs and student mentoring narratives with strict grounding and zero invented statistics.
- **Model Selection Rationale**:
  - **Free-Tier Quota Resilience**: Testing against Google's live API reveals that `gemini-3.6-flash` is subject to an extremely low 20-request/day Free-Tier quota (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), rapidly triggering `429 RESOURCE_EXHAUSTED` during live evaluations. In contrast, `gemini-3.5-flash-lite` provides robust quota headroom.
  - **Sub-Second Latency**: Measured live API response time is ~0.81s per narrative (vs ~3.06s on standard flash models).
  - **Strict Grounding & Prompt Adherence**: Verified live across test cohorts; strictly adheres to calibration disclaimers ($R^2=0.21$, Recall 50%, Precision 33%), factual numbers, and unembellished recommendations.
- **Resilience Strategy**:
  - Primary: `gemini-3.5-flash-lite`
  - Secondary fallback: `gemini-3.5-flash`
  - Zero-downtime offline fallback: Instant deterministic templates containing exact student statistics and honest disclaimers if token is unset, quota is exhausted (60s circuit breaker), or API is unreachable.

---

## Document Consistency Check

| File | Claimed Recall/R² | Matches Live? |
| :--- | :--- | :--- |
| `README.md` | Model 1: `GradientBoostingRegressor`, $R^2 = 0.2096$, $\text{RMSE} = 0.7581$. Model 2: `LogisticRegression`, $\text{Recall} = 50.22\%$, $\text{Precision} = 33.46\%$, $\text{AUC} = 0.5190$. Tech stack (L61) and file tree (L164) both reference `LogisticRegression`. Tech stack (L62) designates `gemini-3.5-flash-lite`. | **Matches Live**: 100% agreement across all algorithms and numerical metrics. |
| `docs/SUBMISSION_GATE_CHECK.md` | Model 1: `GradientBoostingRegressor`, $R^2 = 0.2096$, $\text{RMSE} = 0.7581$, $\text{MAE} = 0.6022$. Model 2: `LogisticRegression`, $\text{Recall} = 0.5022$ ($50.22\%$), $\text{Precision} = 0.3346$ ($33.46\%$), $\text{ROC AUC} = 0.5190$. | **Matches Live**: All algorithms, hyperparameters, and live re-scored metrics match ground truth exactly. |
| `docs/TECHNICAL_DEEP_DIVE.md` | Model 1: `GradientBoostingRegressor`, $R^2 = 0.2096$, $\text{RMSE} = 0.7581$, $\text{MAE} = 0.6022$. Model 2: Section 3.2 (L608–624) and Section 4 summary table (L928) both designate `LogisticRegression` (`C=1.0`, `penalty='l2'`, `solver='liblinear'`, `class_weight='balanced'`) with $\text{Recall} = 0.5022$, $\text{AUC} = 0.5190$, $\text{Precision} = 0.3346$. Section 4.4 and summary table designate `gemini-3.5-flash-lite`. | **Matches Live**: Section 3.2 algorithm and hyperparameters synchronized with Section 4 and live production model object. |
| `docs/ARCHITECTURE.md` | Model 1: `GradientBoostingRegressor`, $R^2 = 0.2096$, $\text{RMSE} = 0.7581$, $\text{MAE} = 0.6022$. Model 2: `Balanced Logistic Regression`, $\text{Recall} = 0.5022$, $\text{Precision} = 0.3346$, $\text{ROC AUC} = 0.5190$, $\text{Accuracy} = 0.5226$. GenAI section 6/7 designates `gemini-3.5-flash-lite`. | **Matches Live**: All algorithms and metrics match live re-scored ground truth exactly. |
| `Arch.html` | Model 1: `GradientBoostingRegressor`, $R^2 = 0.2096$, $\text{RMSE} = 0.7581$. Model 2: Production summaries, swap gains bullet (L3270), and benchmark comparison table (L3500) cite `LogisticRegression` with $\text{Recall} = 0.5022$ ($50.22\%$), $\text{Precision} = 0.3346$, $\text{ROC AUC} = 0.5190$, $\text{Accuracy} = 0.5226$. GenAI ribbon and stat card cite `gemini-3.5-flash-lite`. | **Matches Live**: Benchmark comparison row and swap narratives fully synchronized to retrained production model metrics. |
| `src/dashboard/index.html` | Model 1: `GradientBoostingRegressor`, $R^2 = 0.21$, $\text{RMSE} = 0.76$. Model 2: Text cites $\text{Recall} \approx 0.50$; Model 2 card title/badge (L609) displays `LogisticRegression`. | **Matches Live**: Algorithm badge and metrics fully match active production model. |
| `src/dashboard/app.js` | UI strings cite Model 2 $\text{Recall} = 50.22\%$, $\text{Precision} = 33.46\%$, Model 1 $R^2 = 0.21$. Fallback defaults in `renderModelMetrics()` designate Model 1 $R^2 = 0.2096$, $\text{RMSE} = 0.7581$; Model 2 = `LogisticRegression`, $\text{Recall} = 50.22\%$, $\text{Precision} = 33.46\%$, $\text{ROC AUC} = 0.5190$. GenAI fallback engine designates `gemini-3.5-flash-lite`. | **Matches Live**: Fallback constants match live API data and deployed model ground truth with zero discrepancy. |
| `src/genai/insights.py` | Prompt templates cite Model 1 $R^2 = 0.21$, Model 2 $\text{Recall} = 50\%$ ($0.50$), $\text{Precision} = 33\%$ ($0.33$). `GEMINI_MODEL = "gemini-3.5-flash-lite"` with module docstring designating `gemini-3.5-flash-lite`. Function docstring at line 94 reads `"""Loads Model 2 (LogisticRegression) and metadata."""`. | **Matches Live**: Function docstring and calibration numbers align 100% with live production model. |

---

## One-Line Summary (for quoting in a presentation)

"Model 1: GradientBoostingRegressor, R²=0.2096. Model 2: LogisticRegression, Recall=50.22%, Precision=33.46%, AUC=0.5190. GenAI: Google Gemini (gemini-3.5-flash-lite)."
