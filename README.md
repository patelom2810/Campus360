# Campus360 — Student Academic Success, Early-Warning & Career Readiness Analytics Platform

**Campus360** (KDAC-3) is an end-to-end Student Analytics, Predictive Early-Warning, and Decision-Support Platform. It integrates multi-source academic, behavioral, biometric, and placement records into a unified data engineering warehouse, trains zero-leakage machine learning models, and delivers an interactive Streamlit dashboard with on-demand GenAI faculty mentoring briefings.

---

## 1. Architecture & Project Layout

```text
Campus360/
│
├── config/                            # Central configuration registry
│   ├── __init__.py
│   └── config.py                      # Paths, DB connections, API keys & model registry
│
├── dashboard/                         # Interactive Analytics Web Application
│   └── app.py                         # Streamlit 5-tab executive analytics platform
│
├── data/
│   ├── raw/                           # Immutable raw departmental CSV records (10k+ rows each)
│   │   ├── 1_student_records.csv      # Demographics, CGPA, income, enrollment, at-risk flags
│   │   ├── 2_exam_marks.csv           # Assessments, midterm, consistency, next sem marks
│   │   ├── 3_attendance.csv           # Attendance %, daily/weekly study hours
│   │   ├── 4_lifestyle.csv            # Sleep, screen time, stress, burnout, wellness
│   │   ├── 5_skills.csv               # Resume, interview, aptitude, GitHub, projects
│   │   └── 6_career_preferences.csv   # Hackathons, preferred domains, career goals
│   └── processed/                     # Cleaned relational tables & stitched warehouse
│       ├── cleaned_students.csv
│       ├── cleaned_academic_records.csv
│       ├── cleaned_exam_marks.csv
│       ├── cleaned_attendance.csv
│       ├── cleaned_lifestyle.csv
│       ├── cleaned_skills.csv
│       ├── cleaned_career_preferences.csv
│       ├── student_master_stitched.csv # Unified 10,000-student stitched master dataset
│       └── warehouse.db               # Embedded high-performance SQLite relational warehouse
│
├── docker/                            # Containerization assets
│   ├── Dockerfile                     # Multi-stage Python 3.11 container definition
│   └── entrypoint.sh                  # Container bootstrap & auto-seeding script
│
├── etl/                               # Data Engineering & ETL Pipeline
│   ├── __init__.py
│   ├── extract.py                     # Raw extraction & schema profiling
│   ├── transform.py                   # Key standardization, cleaning & stitching
│   ├── load.py                        # Bulk warehouse loader (foreign-key ordered)
│   ├── validate.py                    # Automated data quality & integrity test suite
│   ├── pipeline.py                    # Master CLI orchestrator
│   └── profiling.py                   # Deep profiling & reconciliation report generator
│
├── genai/                             # Generative AI Mentorship Engine
│   ├── __init__.py
│   └── generate_insights.py           # Gemini 3.6 Flash + Groq fallback student briefing generator
│
├── models/                            # Machine Learning Models & Training Pipelines
│   ├── model_1_performance_regression.py # RandomForestRegressor for next semester marks
│   ├── model_2_at_risk_classifier.py     # RandomForestClassifier for early risk screening
│   ├── next_semester_marks_model.pkl  # Serialized Model 1 artifact
│   └── at_risk_classifier_model.pkl   # Serialized Model 2 artifact
│
├── sql/                               # Relational DDL & Analytical Views
│   ├── schema.sql                     # Relational DDL (7 tables, PKs, FKs, CHECK constraints)
│   └── views.sql                      # Analytical views (Student 360, Feature Views)
│
├── tests/                             # Automated test suites
│   ├── test_etl_pipeline.py           # Data integrity & stitching tests
│   └── test_postgres_migration.py     # PostgreSQL migration & fallback tests
│
├── docker-compose.yml                 # Multi-container orchestration (App + PostgreSQL)
├── Dockerfile                         # Root Dockerfile for direct docker build
├── requirements.txt                   # Production Python dependencies
├── .env.example                       # Environment template
├── .env                               # Active environment configuration
└── README.md                          # Platform documentation
```

---

## 2. Institutional Dataset Sources

| File | Source Division | Original Key Column | Raw Records | Processed Attributes |
| :--- | :--- | :--- | :--- | :--- |
| **`1_student_records.csv`** | Registrar / SIS | `student_id` | 10,080 | CGPA, backlogs, failed subjects, family income, enrollment date, `at_risk_flag`. |
| **`2_exam_marks.csv`** | Controller of Exams | `StudentID` | 10,050 | Internal marks, assignment score, midterm score, consistency, `next_semester_marks`. |
| **`3_attendance.csv`** | LMS & Biometrics | `roll_no` | 10,100 | Attendance rate, daily study hours, weekly self-learning hours. |
| **`4_lifestyle.csv`** | Student Wellness | `student_id` | 10,060 | Sleep hours, screen time, gaming hours, stress level, burnout score, wellness score. |
| **`5_skills.csv`** | Placement & Coding Cell | `STUDENT_ID` | 10,070 | Resume score, mock interview score, communication skills, aptitude, GitHub repos. |
| **`6_career_preferences.csv`** | Career Office | `roll_number` | 10,050 | Hackathon count, preferred tech domain, primary career goal. |

---

## 3. Data Engineering & Stitching Strategy

1. **Non-Positional Key Matching**: Datasets are joined strictly on standardized business key `student_id`. File ordering and physical row index are never assumed.
2. **Key Standardization**: Departmental keys (`StudentID`, `roll_no`, `STUDENT_ID`, `roll_number`) are normalized to `student_id` (`S100000` to `S109999`).
3. **Smart ID Normalization**: The system automatically resolves numeric shorthands:
   - Entering `S900` or `900` automatically resolves to **`S100900`**.
   - Entering `42` automatically resolves to **`S100042`**.
4. **Reconciliation Statistics**:
   - **Total Master Unique Students**: **10,000**
   - **IDs Matched Across All 6 Sources**: **10,000 (100.0% match rate, 0 orphaned students)**.

---

## 4. Relational Data Warehouse & Analytical Views

### Star Schema Design
Centered around the core `students` table:
* **`students`** (`student_id` PK): Core demographics, income, CGPA, and risk flags.
* **`academic_records`** (`student_id` PK/FK): Historical academic marks and performance bands.
* **`exam_marks`** (`student_id` PK/FK): Component assessment marks and target marks.
* **`attendance`** (`student_id` PK/FK): Biometric and coursework attendance records.
* **`lifestyle`** (`student_id` PK/FK): Psychological stress, burnout, sleep, and wellness metrics.
* **`skills`** (`student_id` PK/FK): Placement interview scores, aptitude, and project counts.
* **`career_preferences`** (`student_id` PK/FK): Hackathon participation and career aspirations.

### Analytical SQL Views
* **`student_360_view`**: Denormalized single source of truth joining all 7 domain tables.
* **`performance_features_view`**: Features for Model 1. Strictly omits `next_semester_marks` and `performance_band` to guarantee zero target leakage.
* **`at_risk_features_view`**: Features for Model 2. Combines attendance, academic fragility, and stress metrics.
* **`career_readiness_view`**: Computes a normalized `composite_readiness_score` (0–100) combining resume, interview, aptitude, projects, and hackathons.

---

## 5. Machine Learning Models

### Model 1: Next Semester Marks Regression
* **Task**: Continuous prediction of `next_semester_marks` (0–100).
* **Algorithm**: `RandomForestRegressor(n_estimators=300, max_depth=12, min_samples_leaf=5)`.
* **Key Drivers**: Historical CGPA, lowest subject score, attendance rate, study-to-screen ratio.
* **Artifact**: `models/next_semester_marks_model.pkl`.

### Model 2: At-Risk Early Warning Classifier
* **Task**: Binary classification (`at_risk_flag` $\in \{0, 1\}$).
* **Algorithm**: `RandomForestClassifier(n_estimators=300, max_depth=10, class_weight='balanced')`.
* **Key Drivers**: Wellness score, stress level, burnout score, attendance drop, motivation.
* **Artifact**: `models/at_risk_classifier_model.pkl`.

### Train Models:
```bash
# Train Model 1 (Performance Regression)
python models/model_1_performance_regression.py

# Train Model 2 (At-Risk Classifier)
python models/model_2_at_risk_classifier.py
```

---

## 6. GenAI Faculty Advisory Engine

Campus360 includes an automated GenAI counseling engine that synthesizes the student's 360-degree profile, predictive ML forecasts, and behavioral stressors into an empathetic, actionable 4-part faculty briefing:

1. **Executive Assessment**: Academic health and risk diagnosis.
2. **Critical Risk Factors & Behavioral Flags**: Root causes (e.g. sleep deficit, elevated stress, attendance dips).
3. **Strengths & Bright Spots**: Natural technical competencies and project highlights.
4. **Actionable Mentorship Intervention**: 3 concrete advising steps for the faculty mentor.

* **Primary LLM**: Google Gemini (`gemini-3.6-flash` via `google-genai`).
* **Fallback LLM**: Groq Cloud (`qwen/qwen3.8-27b`).
* **Heuristic Offline Fallback**: Generates structured rule-based briefings if offline.

---

## 7. Interactive Streamlit Dashboard

The web dashboard is organized into 5 dedicated views:

* **Tab 1 — Performance & Grade Bands**: Cohort grade distributions (Excellent, Good, Average, At-Risk), marks histograms, and assessment component breakdowns.
* **Tab 2 — At-Risk Early Warning System**: High-risk student screening, wellness vs. safe comparisons, and risk factor distributions.
* **Tab 3 — Lifestyle & Mental Health**: Daily study vs. marks scatter plots (with OLS trendlines), sleep vs. CGPA analysis, and screen time distributions.
* **Tab 4 — Career & Skill Readiness**: Tech domain distribution, primary career objectives, and domain-wise technical competencies.
* **Tab 5 — Single Student 360 Dossier**: 
  - 1-Click quick presets: 🎲 Random, ⚠️ High Risk (`S100000`), ⚠️ Fragile (`S100001`), ✅ Safe (`S100004`), 🎯 `S900` (`S100900`).
  - Search by full ID (`S100900`), short form (`S900`), or simple number (`900`).
  - On-demand **"✨ Generate AI Faculty Briefing"** button.

---

## 8. Quickstart: Run with Docker (Recommended)

Campus360 is fully containerized and can be launched with a single command:

```bash
# 1. Clone repository and navigate to project root
cd Campus360

# 2. Configure environment keys
cp .env.example .env
# Add your GEMINI_API_KEY and/or GROQ_API_KEY to .env

# 3. Build and launch containers
docker compose up -d --build

# 4. View logs
docker compose logs -f app
```

* **Web Dashboard**: **[http://localhost:8501](http://localhost:8501)**
* **PostgreSQL Warehouse**: `localhost:5433` (`campus360_postgres`)

To stop containers:
```bash
docker compose down
```

---

## 9. Local Development Setup

### Prerequisites
* Python 3.10+
* Virtual environment (`venv`)

### Setup & Run
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full ETL pipeline (Extract -> Transform -> Stitch -> Load -> Validate)
python etl/pipeline.py

# 4. Run automated data quality validation tests
python etl/validate.py

# 5. Launch the Streamlit dashboard
streamlit run dashboard/app.py
```

---

## 10. Data Quality Validation Checks

Running `python etl/validate.py` executes automated tests across 5 quality dimensions:
1. **Row Count & Uniqueness**: Exactly **10,000 distinct students** loaded across all warehouse tables.
2. **Referential Integrity**: **0 orphaned foreign keys** across all child tables.
3. **Domain Constraints**: **0 boundary violations** (CGPA, attendance, percentages, marks, and sleep hours all within valid ranges).
4. **Null Checks**: **0 unexpected nulls** in primary or foreign keys.
5. **Analytical Views**: All 4 views query 10,000 rows without execution errors.
6. **ETL Idempotency**: Running `pipeline.py` multiple times executes safely without duplicating rows.
