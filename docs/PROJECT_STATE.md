# Campus360: Comprehensive Project State & Technical Audit
**Snapshot Date:** September 11, 2026  
**Repository:** `Campus360`  
**Purpose:** Single, comprehensive reference document recording the exact code, data, models, architecture, test results, and limitations of the platform as it currently exists.

---

## 1. Project Identity

- **Hackathon Name:** KENEXA AI Hackathon
- **Problem Code:** KDAC-3
- **Team Name / ID:** Rahil Nagariya & Om Patel (Team ID: 60)
- **Institution:** FCAIT / MSc.IT — GLS University

### Problem Statement & Expected Solution (Verbatim Brief)

> **PROBLEM STATEMENT**  
> Educational institutions collect large amounts of student data—exam results, subject marks, academic records, lifestyle habits, career preferences—but these are often stored separately and rarely analyzed together. Build a platform that integrates multiple datasets through data stitching to analyze academic performance, identify learning gaps, detect at-risk students, predict trends, and enhance career guidance.

> **EXPECTED SOLUTION**  
> An end-to-end platform with data stitching, warehouse design, ETL pipeline, subject-wise analytics dashboards, ML models for performance prediction and at-risk detection, GenAI-powered insights for faculty and mentors, and Dockerized deployment.  
> *Core Tracks:* Data Analytics | Artificial Intelligence / Machine Learning | Data Engineering

---

## 2. Current Folder Structure

Generated via: `find . -type f -not -path '*/venv/*' -not -path '*/.git/*' -not -path '*/__pycache__/*' | sort`

```text
./.DS_Store
./.env
./.env.example
./.gitignore
./PROJECT_STATE.md
./README.md
./data/interim/kundan_clean.csv
./data/interim/navinpatidar_clean.csv
./data/interim/sakharebharat_clean.csv
./data/interim/sehaj_clean.csv
./data/interim/shambhuraje_clean.csv
./data/interim/suvidya_clean.csv
./data/processed/data_lineage.md
./data/processed/dim_student.csv
./data/processed/fact_career.csv
./data/processed/fact_lifestyle.csv
./data/processed/fact_performance.csv
./data/processed/label_engineering_notes.md
./data/processed/model1_performance_test.csv
./data/processed/model1_performance_train.csv
./data/processed/model2_atrisk_test.csv
./data/processed/model2_atrisk_train.csv
./data/processed/pii_removal_log.md
./data/processed/student_master_wide.csv
./data/processed/warehouse.db
./data/raw/kundan_student_performance.csv
./data/raw/navinpatidar_indian_placement.csv
./data/raw/sakharebharat_indian_placement_2025.csv
./data/raw/sehaj_student_lifestyle.csv
./data/raw/shambhuraje_placement_career_2026.csv
./data/raw/suvidya_student_performance.csv
./docker-compose.yml
./docker/Dockerfile.api
./docker/Dockerfile.dashboard
./docs/ARCHITECTURE.md
./docs/DEPLOYMENT.md
./models/label_reconstruction_sanity_check.joblib
./models/label_reconstruction_sanity_check.json
./models/model1_performance_metrics.json
./models/model1_performance_predictor.joblib
./models/model2_atrisk_classifier.joblib
./models/model2_atrisk_metrics.json
./models/reference_diagnostic_atrisk.joblib
./models/reference_diagnostic_metrics.json
./models/suvidya_ceiling_test_comparison.json
./models/suvidya_ceiling_test_lifestyle_only.joblib
./models/suvidya_ceiling_test_with_academic.joblib
./notebooks/eda.ipynb
./requirements.txt
./src/__init__.py
./src/api/__init__.py
./src/api/main.py
./src/dashboard/__init__.py
./src/dashboard/app.js
./src/dashboard/app.py
./src/dashboard/index.html
./src/dashboard/style.css
./src/etl/__init__.py
./src/etl/clean.py
./src/etl/extract.py
./src/etl/fix_and_prepare.py
./src/etl/load.py
./src/etl/run_pipeline.py
./src/etl/stitch.py
./src/genai/__init__.py
./src/genai/insights.py
./src/models/__init__.py
./src/models/train_atrisk_model.py
./src/models/train_atrisk_reference_diagnostic.py
./src/models/train_career_model.py
./src/models/train_performance_model.py
./src/models/train_suvidya_ceiling_test.py
./tests/__init__.py
./tests/test_dashboard_api.py
./tests/test_etl_pipeline.py
./tests/test_fix_and_prepare.py
./tests/test_model_quality.py
./tests/test_postgres_migration.py
```

*Note on root-level files:* The 6 stray root-level CSV files previously present (`Student_Performance.csv`, `Indian_Student_Placement_Dataset_2025.csv`, etc.) were purged during repository housekeeping, leaving `data/raw/` as the single canonical raw source.

---

## 3. Data Layer — What Actually Exists

### 3.1 Raw Source Datasets

All 6 canonical raw datasets are stored in `data/raw/`:

| Canonical Filename | Raw Rows | Raw Columns | What It Contains | Source / Origin |
|---|---|---|---|---|
| `shambhuraje_placement_career_2026.csv` | **25,000** | 44 | Primary demographic spine, degree, branch, CGPA, backlogs, coding telemetry (LeetCode DSA, GitHub repos, hackathons), internships, lifestyle (sleep, screen, stress, burnout), AI tools, placement status & packages. | Shambhuraje (2026) Indian Engineering Placement Survey |
| `kundan_student_performance.csv` | **25,000** | 16 | Secondary school marks (Math, Science, English, Overall Score), letter grade, study hours, attendance %, travel time, parent education, school type. *(Contains 10,000 exact duplicates pruned to 15,000 unique records in `clean.py`)* | Kundan Indian Student Performance dataset |
| `sakharebharat_indian_placement_2025.csv` | **12,000** | 16 | Collegiate placement, CGPA, backlogs, technical projects, certifications, coding/communication ratings (1–10 scale), aptitude score, corporate packages (LPA). | Sakhare Bharat (2025) Engineering Placement Dataset |
| `suvidya_student_performance.csv` | **5,000** | 16 | Intermediate subject marks (Math, Science, English, Previous Year Score, Final Percentage), pass/fail status, attendance %, study hours, parental education. | Suvidya Student Performance Dataset |
| `sehaj_student_lifestyle.csv` | **2,000** | 8 | Daily habit survey: study hours, extracurricular hours, sleep duration, social hours, physical activity hours, stress level (1–5 scale), collegiate GPA (4.0 scale). | Sehaj Sharma Student Lifestyle Dataset (Kaggle) |
| `navinpatidar_indian_placement.csv` | **1,000** | 10 | Corporate placement records: company names, engineering branches, job roles, placement dates, annual packages in INR (`salary_inr`: ₹301,000–₹1,198,000). *(100% placed cohort)* | Navin Patidar Indian Placement Dataset |

### 3.2 Stitching Methodology (Plain Language)

Because higher-education silos share no universal student identifier, the pipeline uses `shambhuraje_placement_career_2026.csv` as the golden anchor spine (25,000 students) and generates immutable institutional identifiers (`STU00001` through `STU25000`). Secondary datasets are partitioned into equal academic performance tertiles (Low, Medium, High) based on their native grading metrics, paired with demographic clusters (Tech, Core Engineering, General; Gender), and sampled without replacement onto anchor students within the exact same performance band. This ensures realistic persona preservation (e.g. an engineering topper is never paired with a failing secondary student) while avoiding artificial record synthesis—unmatched slots naturally remain `NULL` and are tracked with boolean match flags (`has_suvidya_match`, `has_kundan_match`, etc.).

### 3.3 Final Warehouse Schema & Live Row Counts

Queried directly from both `data/processed/*.csv` and the live SQLite warehouse database (`data/processed/warehouse.db`):

| Table Name | Entity Type | Live Row Count | Columns (Extracted Live) |
|---|---|---|---|
| **`dim_student`** | Dimension Table | **25,000** | `student_id`, `gender`, `age`, `stream_branch`, `degree`, `college_tier`, `city_tier`, `state`, `family_income_lpa` |
| **`fact_performance`** | Fact Table (Long Format) | **105,000** | `student_id`, `source`, `assessment_term`, `subject`, `marks`, `max_marks`, `attendance_pct`, `grade_or_status` |
| **`fact_lifestyle`** | Fact Table | **25,000** | `student_id`, `sleep_hours`, `screen_time_hours`, `gaming_hours`, `study_hours_daily`, `stress_level`, `burnout_score`, `gym_frequency_per_week`, `motivation_level`, `physical_activity_hours_sehaj`, `stress_level_sehaj`, `lifestyle_risk_flag` |
| **`fact_career`** | Fact Table | **25,000** | `student_id`, `cgpa`, `backlogs`, `internships`, `dsa_problems_solved`, `github_repos`, `coding_skills_sakhare`, `communication_skills`, `aptitude_score`, `mock_interview_score`, `placement_status`, `company_type`, `work_mode`, `salary_lpa`, `offer_count`, `layoffs_risk_score` |
| **`student_master_wide`** | Master Analytics Flat Table | **25,000** | **116 columns** (all stitched source attributes prefixed by source, match flags, engineered features, and `at_risk_flag`) |

*Relational Constraints:* `dim_student.student_id` serves as the primary key. In PostgreSQL and SQLite DDL, `fact_performance`, `fact_lifestyle`, and `fact_career` enforce foreign keys with `ON DELETE CASCADE` referencing `dim_student(student_id)`.

### 3.4 Live PII Audit Confirmation

A live scan across all processed tables (`dim_student.csv`, `fact_performance.csv`, `fact_lifestyle.csv`, `fact_career.csv`, `student_master_wide.csv`, `model1_performance_*.csv`, `model2_atrisk_*.csv`) executed right now confirms:
- **Columns removed:** Raw columns `navin_name` and `navin_email` from Navin Patidar were dropped in Stage 2 (`clean.py`) and Stage 4 (`fix_and_prepare.py`).
- **Zero PII columns remain:** 0 name columns, 0 email columns, 0 phone/address columns.
- **Regex verification:** An automated regular expression scan (`[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+`) across all string columns returned **0 email pattern matches**.
- **Net row loss from PII pruning:** **0 rows lost** (100% data preservation at 25,000 rows).

---

## 4. Models — Current State, With Full Honesty

All metrics in this section were **reloaded from saved `.joblib` files and re-evaluated against the live test CSVs (`data/processed/*_test.csv`) right now**.

### 4.1 Model 1: Performance Predictor (`models/model1_performance_predictor.joblib`)

- **Model Type:** `GradientBoostingRegressor` (Scikit-Learn, tuned: `n_estimators=200`, `learning_rate=0.05`, `max_depth=3`, `min_samples_leaf=5`, `max_features='sqrt'`).
- **What It Predicts:** Collegiate Cumulative Grade Point Average (`anchor_cgpa`, range 0.0–10.0).
- **Features Used (28 features explicitly):**
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
  25. `effort_score` *(engineered)*
  26. `screen_to_study_ratio` *(engineered)*
  27: `wellness_score` *(engineered)*
  28: `project_activity` *(engineered)*
- **Live Re-Scored Metrics (Evaluated on $N=5,000$ held-out test rows):**
  - **$R^2$ Score:** **0.2096** (CV $R^2 = 0.1843$)
  - **RMSE:** **0.7581**
  - **MAE:** **0.6022**
- **Deployment Status:** **Live in API & Dashboard.** Wired to `POST /api/models/predict-performance` and powers the View 4 interactive slider simulator in the frontend dashboard.
- **Honest Usefulness Sentence:** Weak predictive power ($R^2=0.21$, explaining only 21% of variance in CGPA); useful solely as a directional slider simulation indicating general habits, but cannot be relied on for high-stakes grade forecasting.

### 4.2 Model 2: At-Risk Classifier (`models/model2_atrisk_classifier.joblib`)

- **Model Type:** `RandomForestClassifier` (Scikit-Learn, tuned: `n_estimators=600`, `max_depth=6`, `min_samples_leaf=3`, `class_weight='balanced'`, `decision_threshold=0.50`).
- **What It Predicts:** Binary student at-risk status (`at_risk_flag`: 1 = At-Risk, 0 = Safe).
  *Label Definition:* `at_risk_flag = 1` if (`anchor_backlog_history >= 1` OR `anchor_attendance_percentage < 55` OR `anchor_cgpa < 5.5`), else `0`. Population balance is 31.9% at-risk (7,975 students) vs 68.1% safe (17,025 students).
- **Features Used (23 features explicitly — strictly non-leaked lifestyle, habits, and skills):**
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
  22. `wellness_score` *(engineered)*
  23. `screen_to_study_ratio` *(engineered)*  
  *Strictly Excluded Leakage Columns:* `anchor_attendance_percentage`, `anchor_backlog_history`, and `anchor_cgpa` were strictly excluded because they constitute the mathematical definition of the target.
- **Live Re-Scored Metrics (Evaluated on $N=5,000$ held-out test rows):**
  - **ROC AUC:** **0.5044**
  - **Accuracy:** **0.5232** (52.3%)
  - **Recall (Class 1 - At-Risk):** **0.4514** (45.1% of at-risk students identified)
  - **Precision (Class 1 - At-Risk):** **0.3230**
  - **F1 Score (Class 1):** **0.3766**
  - **Confusion Matrix:**
    $$\begin{bmatrix} \text{TN: } 1,896 & \text{FP: } 1,509 \\ \text{FN: } 875 & \text{TP: } 720 \end{bmatrix}$$
- **Deployment Status:** **Live in API & Dashboard.** Wired to `GET /api/models/atrisk-metadata`, `GET /api/analytics/atrisk-table`, `GET /api/analytics/at-risk-students`, and `GET /api/students/{id}` with mandatory on-screen disclosure text.
- **Honest Usefulness Sentence:** Functionally equivalent to random chance (ROC AUC = 0.5044, catching only 45% of at-risk students), demonstrating that lifestyle and survey attributes alone contain almost zero predictive signal for statutory academic failure in this synthetic dataset without academic telemetry.

### 4.3 Label Reconstruction Sanity Check (`models/label_reconstruction_sanity_check.joblib`)

- **Model Type:** `RandomForestClassifier` (`n_estimators=200`, `max_depth=8`).
- **What It Predicts:** `at_risk_flag` (1 vs 0).
- **Features Used (26 features explicitly):** The 23 lifestyle/skill features PLUS the 3 label-defining academic columns (`anchor_backlog_history`, `anchor_attendance_percentage`, `anchor_cgpa`).
- **Live Re-Scored Metrics (Evaluated on $N=5,000$ held-out test rows):**
  - **ROC AUC:** **1.0000**
  - **Accuracy:** **1.0000** (100.0%)
  - **Recall:** **1.0000**
  - **Precision:** **1.0000**
  - **F1 Score:** **1.0000**
  - **Confusion Matrix:**
    $$\begin{bmatrix} 3,405 & 0 \\ 0 & 1,595 \end{bmatrix}$$
- **Deployment Status:** **Reference / Diagnostic Only.** Stored in `models/label_reconstruction_sanity_check.joblib` and `models/reference_diagnostic_atrisk.joblib`. Not wired to API inference or dashboard predictions.
- **Honest Usefulness Sentence:** A circular mathematical sanity check confirming that the random forest recovers the exact threshold formula used to engineer `at_risk_flag` (91.2% feature importance on `anchor_backlog_history`), providing engineering verification of data integrity but zero real-world predictive value.

### 4.4 Suvidya Ceiling Test Models (`models/suvidya_ceiling_test_*.joblib`)

- **Model Types:** Two `RandomForestClassifier` models evaluated strictly on the $N=5,000$ Suvidya-matched subcohort (`has_suvidya_match == 1`, 80/20 train/test split: 4,000 train, 1,000 test with 53 fail cases).
- **What It Predicts:** `suvidya_pass_fail` mapped to binary ground truth (1 = Fail, 0 = Pass) from an external, independently sourced dataset.
- **Live Re-Scored Metrics (Evaluated on held-out 1,000 rows):**
  - **Model A (Lifestyle Only — 23 features):**
    - ROC AUC: **0.6065**
    - Recall (Fail): **0.1698** (17.0%)
    - Precision (Fail): **0.1324**
    - Accuracy: **0.8970** | F1: **0.1488**
  - **Model B (Lifestyle + Academic Context — 26 features):**
    - ROC AUC: **0.8728** ($\Delta \text{AUC} = +0.2663$)
    - Recall (Fail): **0.6792** (67.9%)
    - Precision (Fail): **0.1773**
    - Accuracy: **0.8160** | F1: **0.2812**
- **Deployment Status:** **Reference / Methodology Validation Only.** Not exposed in the API or dashboard.
- **Honest Usefulness Sentence:** While Model B appears to show strong predictive lift from academic context (AUC 0.61 $\rightarrow$ 0.87), this finding is heavily confounded by the fact that `anchor_cgpa` was the exact stitching key used to match Suvidya records ($r=0.807$), with `anchor_cgpa` carrying 59.32% of Model B's feature importance—meaning the observed lift is largely an artifact of the stitching algorithm rather than genuine real-world linkage.

---

## 5. Backend API — What's Actually Live

Implemented in `src/api/main.py` using **FastAPI 0.141.1**:

| HTTP Method | Route Path | Purpose & What It Returns | Wired to Live DB / Model or Stub? |
|---|---|---|---|
| `GET` | `/` | Platform metadata: status, version, active DB engine (`postgres` or `sqlite`), endpoint catalog, and URLs for `/dashboard` and `/docs`. | **Live:** Queries active DB engine dynamically. |
| `GET` | `/health` | Deep health check: verifies database connection, live row counts for all 4 warehouse tables (`dim_student`, `fact_performance`, `fact_lifestyle`, `fact_career`), and file presence of Model 1 & 2 `.joblib` artifacts. | **Live DB Query + File Check:** Returns 500 if DB or models are missing. |
| `GET` | `/api/students` | Paginated student list (`limit`, `offset`) with optional SQL filters (`stream_branch`, `college_tier`, `state`). Returns total student count and matching rows. | **Live DB Query:** Executes parameterized SQL query against `dim_student`. |
| `GET` | `/api/students/{student_id}` | Complete Student 360 profile: demographic record, long-format academic history across sources (`fact_performance` with normalized %), lifestyle metrics (`fact_lifestyle`), career placement (`fact_career`), and live Model 2 at-risk score with top contributing factor. | **Live DB + Live Model Cache:** Queries 4 tables and matches precomputed Model 2 inference matrix. |
| `GET` | `/api/analytics/overview` | Warehouse KPI aggregates (total students, average CGPA, placement rate %, calibrated at-risk %, high-risk lifestyle %, average salary LPA) and CGPA distribution histogram bins. | **Live DB Queries:** Computes live SQL `AVG()`, `COUNT()`, and `CASE` histograms. |
| `GET` | `/api/analytics/at-risk-students` | Top flagged at-risk students ordered by predicted probability from Model 2. Returns student ID, CGPA, predicted risk probability, branch, tier, and top contributing risk factor. | **Live Model Inference:** Evaluates Model 2 probabilities and computes z-score feature deviations across `student_master_wide.csv`. |
| `GET` | `/api/analytics/subjects` | Normalized subject-wise performance: overall subject averages, branch $\times$ subject heatmap matrix, and lowest-performing subject per branch. Directs 0–10 scale (CGPA) and 0–100 scale (exams) onto a unified 0–100% scale. | **Live DB Query + Aggregation:** Executes SQL `JOIN` of `fact_performance` and `dim_student`, aggregated in pandas. |
| `GET` | `/api/models/atrisk-metadata` | Model 2 specification: model name, decision threshold (0.50), recall (0.4514), precision (0.3230), ROC AUC (0.5044), calibrated population split, top 5 feature importances, and mandatory clinical disclosure text. | **Live File Read:** Reads directly from `models/model2_atrisk_metrics.json`. |
| `GET` | `/api/analytics/atrisk-table` | Paginated and searchable (`student_id`) table of all students ranked by predicted risk probability, current CGPA, and top contributing factor. | **Live Model Inference Cache:** Scored via Model 2 over the feature matrix. |
| `POST` | `/api/models/predict-performance` | Interactive what-if simulator: accepts telemetry sliders (attendance %, study hours, DSA solved, internships, sleep hours, communication skills), imputes medians for non-slider features, calculates 4 interaction terms, runs `model1_performance_predictor.joblib`, and returns predicted CGPA with $R^2=0.21$ caveat. | **Live ML Inference:** Executes `model1.predict()` in real-time. |
| `GET` | `/api/analytics/departments` | Aggregated breakdown by engineering branch: student count, average CGPA, average salary (LPA), and placed count. | **Live DB Query:** Executes SQL `GROUP BY stream_branch` joining `dim_student` and `fact_career`. |
| `MOUNT` | `/dashboard` | Mounts static directory `src/dashboard/` to serve the HTML5/Tailwind web app directly from FastAPI. | **Live Static File Mount.** |

*Stub Assessment:* **Zero placeholder/stub endpoints.** Every endpoint connects to real PostgreSQL/SQLite queries, live loaded Scikit-Learn models, or real serialized metric metadata.

---

## 6. Dashboard — What's Actually Built

There are **two distinct dashboard implementations** currently present in `src/dashboard/`:

### 6.1 Modern HTML5 + Tailwind CSS + Vanilla JS Dashboard (`index.html`, `app.js`, `style.css`)
Mounted at `http://localhost:8000/dashboard` and served directly by FastAPI. It contains 5 navigable views:

1. **View 1: Executive Overview (`#view-overview`)**
   - *Status:* Fully implemented.
   - *Live vs Hardcoded:* **100% Live.** Fetches `GET /api/analytics/overview` (renders 6 KPI metric cards and a Chart.js CGPA distribution bar chart), `GET /api/analytics/at-risk-students?limit=6` (renders the urgent at-risk alert cards), and `GET /api/analytics/departments` (renders the departmental table).
2. **View 2: Subject-Wise Performance & Learning Gaps (`#view-subjects`)**
   - *Status:* Fully implemented.
   - *Live vs Hardcoded:* **100% Live.** Fetches `GET /api/analytics/subjects`. Renders an overall subject bar chart, a dynamic CSS grid Branch $\times$ Subject performance heatmap matrix, and a diagnostic table of the lowest-performing subject per engineering branch.
3. **View 3: At-Risk Early Detection & Disclosed Diagnostics (`#view-atrisk`)**
   - *Status:* Fully implemented.
   - *Live vs Hardcoded:* **100% Live.** Fetches `GET /api/models/atrisk-metadata` (renders the model recall, precision, AUC, and mandatory disclosure banner) and `GET /api/analytics/atrisk-table` (renders a paginated, searchable table of all students with predicted risk probabilities and server-calculated top contributing risk factors).
4. **View 4: Performance Prediction Simulator (`#view-predict`)**
   - *Status:* Fully implemented.
   - *Live vs Hardcoded:* **100% Live.** Interactively sends `POST /api/models/predict-performance` on every slider adjustment (Attendance, Daily Study, DSA Problems, Internships, Sleep, Communication Skills). Displays live predicted CGPA and the transparent $R^2=0.21$ confidence alert.
5. **View 5: Student 360 Institutional Dossier (`#view-student`)**
   - *Status:* Fully implemented.
   - *Live vs Hardcoded:* **100% Live.** Accepts any Student ID (`STU00001`–`STU25000`), fetches `GET /api/students/{id}`, and populates demographics, model risk indicator, full subject examination marks across sources, lifestyle habits/wellness flags, and placement/coding profiles.

### 6.2 Streamlit Dashboard (`src/dashboard/app.py`)
Configured to run standalone on port 8501 via `streamlit run src/dashboard/app.py`.
- *Tabs:* Executive Overview, Academic Performance, Lifestyle & Mental Wellness, Placement & Career Readiness, Student 360 Explorer.
- *Status:* Operational. Directly queries PostgreSQL/SQLite via SQLAlchemy and renders Plotly charts.
- *Caveat:* Does not include the Model 1 interactive what-if slider or the Model 2 risk prediction table (those exist in the HTML5 dashboard).

### 6.3 Features Described in Past Planning Documents That Were NOT Implemented
- **Role-Based Authentication:** The original plan (`IMPLEMENTATION_PLAN.md` from commit `0bf26ad`) described Django role-based login views (`Faculty`, `Student`, `Admin`). **This was never built.** The dashboard has no authentication, login sessions, or role restrictions.
- **Django Framework:** Django was completely abandoned in favor of FastAPI + static HTML5/Tailwind frontend.
- **GenAI Copilot Chat Interface:** No faculty copilot chat window or mentor Q&A prompt interface was ever built into either dashboard.

---

## 7. GenAI Insights Layer

- **File Status:** `src/genai/insights.py` is **completely empty (0 bytes)**.
- **Package Status:** `src/genai/__init__.py` is **0 bytes**.
- **Implementation State:** **Not implemented.** There is currently zero code connecting to LLMs (Gemini, Claude, or OpenAI). No prompt templates, faculty intervention summaries, or student recommendations have been coded.

---

## 8. Docker & Deployment

### 8.1 Docker Services Defined (`docker-compose.yml`)

Three services are defined:
1. `postgres`: `postgres:16` image on port `5432:5432`, mounting volume `pgdata`, with healthcheck `pg_isready -U campus360`.
2. `api`: Builds from `docker/Dockerfile.api` (Python 3.11-slim, installing `requirements.txt` and running `uvicorn src.api.main:app` on port `8000`).
3. `dashboard`: Builds from `docker/Dockerfile.dashboard` (Python 3.11-alpine, running `python -m http.server 8501` serving `src/dashboard/`).

### 8.2 Actual Execution Status of Docker Compose
- **Has `docker-compose up` been run successfully end-to-end?** **NO.**
- **Verification:** Docker is not installed on this host environment (`zsh: command not found: docker`).
- **Validation:** The Docker configuration was validated solely via automated Python unit tests (`tests/test_postgres_migration.py:test_docker_compose_config`), which confirmed syntax and structure. It has **never been launched as live containers** in this development environment.

### 8.3 Database Configuration: PostgreSQL vs. SQLite Fallback
- **Active Production Database:** PostgreSQL 16 is running natively on `localhost:5432` (`campus360_warehouse`), verified via live connection with `psycopg2`.
- **Automatic SQLite Fallback:** Implemented in `src/etl/load.py` (`create_warehouse_engine`). If `DB_ENGINE=sqlite` is set or if PostgreSQL connection fails, the system automatically falls back to `data/processed/warehouse.db` with zero breaking changes or API schema divergence.

---

## 9. Tests

### 9.1 Test Files & Test Case Breakdown

| Test File | Framework / Type | Test Count | Test Methods Implemented |
|---|---|---|---|
| `tests/test_dashboard_api.py` | `unittest.TestCase` (Integration) | **8** | `test_healthcheck`, `test_analytics_overview`, `test_at_risk_students_quicklist`, `test_subject_performance_normalization`, `test_atrisk_metadata_and_disclosure`, `test_atrisk_table_pagination_and_search`, `test_performance_prediction_sensitivity`, `test_student_360_lookup` |
| `tests/test_etl_pipeline.py` | `unittest.TestCase` (ETL Quality) | **5** | `test_raw_files_exist`, `test_interim_files_clean`, `test_wide_master_integrity`, `test_star_schema_relationships`, `test_statistical_realism` |
| `tests/test_fix_and_prepare.py` | `unittest.TestCase` (Data Engineering) | **5** | `test_artifacts_exist`, `test_pii_completely_removed`, `test_kundan_final_grade_casing`, `test_model1_dataset_integrity`, `test_model2_dataset_integrity_and_leakage` |
| `tests/test_postgres_migration.py` | `unittest.TestCase` (DB & Fallback) | **6** | `test_requirements_and_env`, `test_postgres_table_counts_match_csvs`, `test_sqlite_fallback_table_counts`, `test_foreign_key_constraints_enforced`, `test_api_postgres_and_sqlite_parity`, `test_docker_compose_config` |
| `tests/test_model_quality.py` | Standalone CLI Verification Script | **6 steps** | Reloads & verifies Model 1 and Model 2 metrics, checks thresholds, verifies train/test splits, tests for data leakage, and confirms uniform feature importances. |

### 9.2 Full Test Suite Execution Results

Executed live via `venv/bin/python -m unittest discover tests -v`:

```text
test_analytics_overview (test_dashboard_api.TestDashboardAPI.test_analytics_overview) ... ok
test_at_risk_students_quicklist (test_dashboard_api.TestDashboardAPI.test_at_risk_students_quicklist) ... ok
test_atrisk_metadata_and_disclosure (test_dashboard_api.TestDashboardAPI.test_atrisk_metadata_and_disclosure) ... ok
test_atrisk_table_pagination_and_search (test_dashboard_api.TestDashboardAPI.test_atrisk_table_pagination_and_search) ... ok
test_healthcheck (test_dashboard_api.TestDashboardAPI.test_healthcheck) ... ok
test_performance_prediction_sensitivity (test_dashboard_api.TestDashboardAPI.test_performance_prediction_sensitivity) ... ok
test_student_360_lookup (test_dashboard_api.TestDashboardAPI.test_student_360_lookup) ... ok
test_subject_performance_normalization (test_dashboard_api.TestDashboardAPI.test_subject_performance_normalization) ... ok
test_interim_files_clean (test_etl_pipeline.TestETLPipeline.test_interim_files_clean) ... ok
test_raw_files_exist (test_etl_pipeline.TestETLPipeline.test_raw_files_exist) ... ok
test_star_schema_relationships (test_etl_pipeline.TestETLPipeline.test_star_schema_relationships) ... ok
test_statistical_realism (test_etl_pipeline.TestETLPipeline.test_statistical_realism) ... ok
test_wide_master_integrity (test_etl_pipeline.TestETLPipeline.test_wide_master_integrity) ... ok
test_artifacts_exist (test_fix_and_prepare.TestFixAndPrepare.test_artifacts_exist) ... ok
test_kundan_final_grade_casing (test_fix_and_prepare.TestFixAndPrepare.test_kundan_final_grade_casing) ... ok
test_model1_dataset_integrity (test_fix_and_prepare.TestFixAndPrepare.test_model1_dataset_integrity) ... ok
test_model2_dataset_integrity_and_leakage (test_fix_and_prepare.TestFixAndPrepare.test_model2_dataset_integrity_and_leakage) ... ok
test_pii_completely_removed (test_fix_and_prepare.TestFixAndPrepare.test_pii_completely_removed) ... ok
test_api_postgres_and_sqlite_parity (test_postgres_migration.TestPostgresMigration.test_api_postgres_and_sqlite_parity) ... ok
test_docker_compose_config (test_postgres_migration.TestPostgresMigration.test_docker_compose_config) ... ok
test_foreign_key_constraints_enforced (test_postgres_migration.TestPostgresMigration.test_foreign_key_constraints_enforced) ... ok
test_postgres_table_counts_match_csvs (test_postgres_migration.TestPostgresMigration.test_postgres_table_counts_match_csvs) ... ok
test_requirements_and_env (test_postgres_migration.TestPostgresMigration.test_requirements_and_env) ... ok
test_sqlite_fallback_table_counts (test_postgres_migration.TestPostgresMigration.test_sqlite_fallback_table_counts) ... ok

----------------------------------------------------------------------
Ran 24 tests in 1.440s

OK (24 passed, 0 failed, 0 errors)
```

In addition, `venv/bin/python tests/test_model_quality.py` completed with exit code `0`, confirming all saved model artifacts match test evaluation metrics within numerical tolerance.

---

## 10. Known Issues, Limitations & Honest Caveats

### 1. Model 1 Weak Performance ($R^2 = 0.2096$)
- **Issue:** The Gradient Boosting Regressor predicting CGPA achieves an $R^2$ of only 0.2096 (RMSE: 0.7581, MAE: 0.6022).
- **Root Cause:** Synthetic and self-reported habit attributes (study hours, sleep, stress, DSA problems solved) have high variance and relatively weak correlation with cumulative collegiate CGPA.
- **Handling in Platform:** The API and frontend explicitly disclose this limitation on screen ("$R^2$ is 0.21 — provides directional guidance but should not be treated as a definitive grade prediction").

### 2. Model 2 Near-Random Classification (ROC AUC = 0.5044, Recall = 0.4514)
- **Issue:** The Random Forest Classifier predicting `at_risk_flag` from lifestyle features performs at essentially chance level (ROC AUC = 0.5044, Recall = 0.4514, Precision = 0.3230).
- **Root Cause:** `at_risk_flag` was engineered strictly from academic deficit indicators (`backlogs >= 1`, `attendance < 55%`, `cgpa < 5.5`). To prevent data leakage, these defining features were strictly excluded. In this synthetic dataset, lifestyle habits (sleep, screen time, gym frequency) have virtually zero organic predictive relationship with statutory academic failure.
- **Handling in Platform:** The dashboard displays a mandatory prominent disclosure banner: *"This model correctly identifies ~45% of at-risk students (recall 0.45) using lifestyle and behavioral data alone. Absence of a flag does not rule out risk."*

### 3. Stitching-Induced Confound on Suvidya Ceiling Test
- **Issue:** On the non-circular ceiling test (`suvidya_pass_fail`), adding academic telemetry shows an apparent jump in ROC AUC from 0.6065 to 0.8728.
- **Root Cause:** In Stage 3 (`stitch.py`), `anchor_cgpa` was used as the primary tertile matching key to stitch Suvidya records onto anchor students ($r = 0.807$). Consequently, `anchor_cgpa` carries 59.32% of Model B's feature importance. The observed "predictive lift" is largely an artifact of the stitching algorithm's own matching rules rather than an organic real-world finding.

### 4. Circular Sanity Check
- **Issue:** `label_reconstruction_sanity_check.joblib` achieves 100% accuracy and 1.0000 ROC AUC.
- **Caveat:** This is a deterministic recovery check proving that a tree model can reconstruct the threshold logic (`backlog >= 1 OR attendance < 55 OR cgpa < 5.5`) when given those exact columns. It is an engineering validation step, not machine learning.

### 5. Incomplete / Stubbed Modules
- **`src/genai/insights.py`:** Completely empty (0 bytes). No GenAI copilot or prompt generation exists.
- **`src/models/train_career_model.py`:** Completely empty (0 bytes). Career readiness scoring model was never trained.

### 6. Discrepancies Between Current State and Earlier Documentation
- **Dashboard Architecture:** Earlier documentation (`0bf26ad:IMPLEMENTATION_PLAN.md`) specified a Django dashboard with role-based logins (Faculty / Student / Admin) and Plotly charts. In reality, Django and authentication were dropped in favor of a unified FastAPI backend serving an HTML5/Tailwind/Chart.js single-page application and an offline Streamlit alternative.
- **Master Wide Table Column Count:** Earlier docs cite 112 or 113 columns; live querying reveals **116 columns** in `student_master_wide.csv` due to the inclusion of 4 engineered features (`effort_score`, `screen_to_study_ratio`, `wellness_score`, `project_activity`) and `at_risk_flag`.
- **Docker Environment:** Previous documentation implied full Docker containerization; however, Docker is not installed on this host machine, meaning `docker compose up` has never been verified end-to-end.

---

## 11. What's Left To Do

A prioritized punch-list of remaining work required to fully satisfy the problem statement's **Expected Solution** ("An end-to-end platform with data stitching, warehouse design, ETL pipeline, subject-wise analytics dashboards, ML models for performance prediction and at-risk detection, GenAI-powered insights for faculty and mentors, and Dockerized deployment"):

1. **Implement GenAI Insights Layer (`src/genai/insights.py`)**
   - Wire an LLM provider (Google Gemini API via `google-genai` or Anthropic API via `anthropic`).
   - Implement faculty copilot prompts that consume a student's 360 profile and generate plain-language diagnostic intervention plans.
   - Expose a FastAPI endpoint (`POST /api/genai/student-insights`) and add an AI Copilot drawer/tab in the dashboard.

2. **Implement Career Readiness Model (`src/models/train_career_model.py`)**
   - Populate `src/models/train_career_model.py` to train a career placement / readiness model using `fact_career` attributes (DSA problems solved, internships, coding skills, CGPA).
   - Save artifacts to `models/model3_career_readiness.joblib` and integrate inference into the API and dashboard.

3. **Install Docker Desktop & Verify Multi-Container Orchestration**
   - Install Docker Desktop on macOS.
   - Execute `docker compose up --build` end-to-end.
   - Verify network resolution and container healthchecks between `campus360_postgres`, `campus360_api`, and `campus360_dashboard`.

4. **Model 2 Feature Exploration**
   - Explore whether non-leaking academic proxies (e.g. historical school marks from Kundan or Suvidya on matched cohorts) can raise Model 2 recall above 0.50 without introducing circular leakage from the anchor defining columns.

5. **Repository Housekeeping (Completed)**
   - [DONE] Completed: Purged the 6 stray unstandardized CSV files from the project root (`Student_Performance.csv`, `Indian_Student_Placement_Dataset_2025.csv`, `Student_Performance_Dataset.csv`, `Student_Performance_Dataset (1).csv`, `indian_student_placement_data.csv`, `student_placement_career_success_dataset.csv`). All ETL and training pipelines continue to draw strictly from `data/raw/`.
