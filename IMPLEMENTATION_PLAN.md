# KDAC-3: Student Academic Success, Subject Performance & Career Readiness Analytics Platform
## Full Implementation Plan

**Team:** Rahil Nagariya & Om Patel | Team ID: 60  
**College:** FCAIT / MSc.IT — GLS University  
**Hackathon:** KENEXA AI Hackathon  
**Problem Code:** KDAC-3

---

## 1. Project Overview

Build an end-to-end **Student Success Intelligence Platform** that:
- Integrates fragmented student data into a unified 360° student profile
- Detects at-risk students early with ML-powered prediction + SHAP explanations
- Identifies subject-level learning gaps via analytics dashboards
- Calculates career readiness scores and skill gaps per student
- Generates plain-language faculty/mentor recommendations via a GenAI copilot
- Deploys fully Dockerized for institutional use

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, Tailwind CSS, Django Templates |
| Backend | Python, Django / FastAPI |
| Data Engineering | Pandas, NumPy |
| ETL & Data Stitching | Pandas, Python (completed ✅) |
| Database | PostgreSQL |
| Data Warehouse | PostgreSQL — Star Schema |
| Analytics | Pandas, NumPy, SQL |
| Visualization | Plotly |
| Machine Learning | Scikit-learn, XGBoost |
| GenAI Insights | Gemini API / OpenAI API |
| Deployment | Docker, Docker Compose |
| Version Control | Git, GitHub |

---

## 3. Current Status (Completed ✅)

The data stitching and warehouse design layer is **fully complete**:

```
data/processed/v5/
├── dim_student.csv          — 1,200 students, MSTU##### IDs
├── dim_cs_skills_v5.csv     — 180 CS student skill profiles
├── fact_risk_behaviour.csv  — 36 survey/risk behaviour columns
├── fact_placement.csv       — placement outcomes + career skills
├── fact_subject_marks.csv   — UCI subject marks (long format)
├── fact_skill_scores.csv    — 10 skills, two scale types
├── data_quality_report.md
├── data_lineage_v5.md
├── null_handling_report.md
└── removed_columns.md
```

**27/27 QA checks passed. 511 documented null imputations. Zero fabricated values.**

---

## 4. Architecture — End-to-End Data Flow

```
Raw CSVs (data/raw/)
        │
        ▼
[ETL / Stitching Layer — DONE ✅]
  stitch_v5.py → data/processed/v5/
        │
        ▼
[PostgreSQL Data Warehouse]
  Star Schema: dim_student + fact_* tables
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
[Analytics Engine]                    [ML Models]
  Pandas + SQL + Plotly                Scikit-learn / XGBoost
  Subject performance                  Risk classifier
  Attendance trends                    Performance predictor
  Skill gap heatmaps                   Career readiness scorer
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
              [GenAI Copilot Layer]
               Gemini API / OpenAI
               Faculty Q&A interface
               Personalized recommendations
                       │
                       ▼
              [Django Web Dashboard]
               Role-based views:
               Faculty | Student | Admin
```

---

## 5. Implementation Phases

---

### PHASE 1 — Data Engineering & Warehouse ✅ COMPLETE

**Goal:** Clean, stitched, warehouse-ready star schema  
**Status:** Done

| Deliverable | Status |
|---|---|
| Source data profiling (12 files) | ✅ Done |
| Null handling (511 nulls, documented) | ✅ Done |
| Star schema (6 tables) | ✅ Done |
| Data quality report | ✅ Done |
| Data lineage report | ✅ Done |

---

### PHASE 2 — PostgreSQL Warehouse Setup

**Goal:** Load v5 star schema into PostgreSQL

#### 2.1 Database Schema (DDL)

```sql
-- Dimension: Students
CREATE TABLE dim_student (
    master_student_id   VARCHAR(10) PRIMARY KEY,
    src_risk_training_id VARCHAR(10),
    year_class          VARCHAR(50),
    program_stream      VARCHAR(50),
    age                 INT,
    gender              VARCHAR(20)
);

-- Dimension: CS Skills
CREATE TABLE dim_cs_skills (
    cs_ref_id           VARCHAR(10) PRIMARY KEY,
    src_cs_student_id   INT,
    gender              VARCHAR(20),
    age                 INT,
    gpa_4               FLOAT,
    gpa_10              FLOAT,
    interested_domain   VARCHAR(100),
    python_skill        VARCHAR(20),
    sql_skill           VARCHAR(20),
    java_skill          VARCHAR(20),
    future_career       VARCHAR(100)
);

-- Fact: Risk Behaviour
CREATE TABLE fact_risk_behaviour (
    master_student_id   VARCHAR(10) REFERENCES dim_student,
    cgpa_category       VARCHAR(20),
    academic_satisfaction VARCHAR(50),
    attendance_band     VARCHAR(30),
    study_hours_daily   VARCHAR(30),
    daily_productivity  FLOAT,
    stress_level        FLOAT,
    energy_level        FLOAT,
    sleep_hours         VARCHAR(30),
    performance_risk_level VARCHAR(20),
    risk_label_available BOOLEAN,
    -- + all other survey columns
    PRIMARY KEY (master_student_id)
);

-- Fact: Placement
CREATE TABLE fact_placement (
    master_student_id         VARCHAR(10) REFERENCES dim_student,
    placement_status          VARCHAR(20),
    salary_package_lpa        FLOAT,
    internships_count         INT,
    projects_count            INT,
    certifications_count      INT,
    coding_skill_score        FLOAT,
    aptitude_score            FLOAT,
    pl_communication_skill_score FLOAT,
    logical_reasoning_score   FLOAT,
    college_tier              VARCHAR(20),
    is_synthetic_placement_match BOOLEAN,
    PRIMARY KEY (master_student_id)
);

-- Fact: Subject Marks (long format)
CREATE TABLE fact_subject_marks (
    uci_ref_id      VARCHAR(15),
    subject_id      VARCHAR(5),
    subject_name    VARCHAR(50),
    grade_period    VARCHAR(5),
    marks           FLOAT,
    max_marks       INT,
    percentage      FLOAT,
    source          VARCHAR(50),
    is_synthetic    BOOLEAN,
    PRIMARY KEY (uci_ref_id, subject_id, grade_period)
);

-- Fact: Skill Scores (long format)
CREATE TABLE fact_skill_scores (
    master_student_id VARCHAR(10) REFERENCES dim_student,
    skill             VARCHAR(30),
    score             FLOAT,
    score_scale       VARCHAR(10),
    source            VARCHAR(50),
    is_synthetic_match BOOLEAN,
    PRIMARY KEY (master_student_id, skill)
);
```

#### 2.2 ETL Load Script

File: `etl/load_to_postgres.py`
- Load all v5 CSVs into PostgreSQL using `psycopg2` / `SQLAlchemy`
- Validate FK integrity after load
- Create indexes on `master_student_id`, `performance_risk_level`, `placement_status`

---

### PHASE 3 — Analytics Engine

**Goal:** Compute subject analytics, risk summaries, skill gap insights

#### 3.1 Subject Performance Analytics (`analytics/subject_analytics.py`)
- Average marks per subject (Mathematics vs Portuguese)
- Grade distribution (G1 → G2 → G3 progression trends)
- Failure rate by school, age group, study time band
- Heatmap: subject × grade period performance

#### 3.2 Risk Behaviour Analytics (`analytics/risk_analytics.py`)
- Distribution of `performance_risk_level` (Low / Moderate / High)
- Risk by program stream, year class, CGPA band
- Study hours vs risk correlation
- Attendance band vs risk breakdown

#### 3.3 Placement & Career Analytics (`analytics/placement_analytics.py`)
- Placement rate overall and by college tier
- Salary distribution for placed students
- Skill scores vs placement outcome
- Skill gap: what skills do unplaced students lack?

#### 3.4 Career Readiness Score (`analytics/career_readiness.py`)

Composite score (0–100) per student:

| Component | Weight | Source |
|---|---|---|
| Technical Skills | 30% | `coding_skill_score`, `skill_score_*` |
| Academic Performance | 20% | `cgpa_category`, `academic_satisfaction` |
| Communication | 15% | `pl_communication_skill_score` |
| Problem Solving | 15% | `logical_reasoning_score`, `aptitude_score` |
| Projects | 10% | `projects_count` |
| Certifications | 5% | `certifications_count` |
| Interview Skills | 5% | `mock_interview_score` |

---

### PHASE 4 — Machine Learning Models

**Goal:** Risk classification, performance prediction, career readiness prediction

#### 4.1 At-Risk Student Classifier (`models/risk_classifier.py`)

- **Target:** `performance_risk_level` (Low / Moderate / High)
- **Features:** study_hours_daily, stress_level, energy_level, attendance_band,
  daily_productivity, revision_frequency, cgpa_category, sleep_hours,
  tasks_on_time, assignments_on_time, programming_foundation
- **Model:** XGBoost (handles ordinal categoricals well)
- **Class imbalance:** SMOTE (Moderate Risk=572, High Risk=452, Low Risk=176)
- **Explainability:** SHAP values → top 3 risk factors per student
- **Threshold tuning:** Optimize for High Risk recall (early intervention priority)
- **Metrics:** F1-macro, Precision, Recall, Confusion Matrix

#### 4.2 Placement Predictor (`models/placement_predictor.py`)

- **Target:** `placement_status` (Placed / Not Placed)
- **Features:** cgpa_category, coding_skill_score, aptitude_score,
  communication_skill_score, internships_count, projects_count,
  hackathons_participated, college_tier, backlogs
- **Model:** XGBoost Classifier
- **Metrics:** Accuracy, AUC-ROC, F1

#### 4.3 Career Readiness Regressor (`models/career_readiness_model.py`)

- **Target:** Computed career readiness score (0–100)
- **Features:** skill scores, academic performance, project count
- **Model:** Random Forest Regressor
- **Output:** Score + top skill gaps per student

#### 4.4 Model Training Pipeline

```
models/
├── risk_classifier.py
├── placement_predictor.py
├── career_readiness_model.py
├── feature_engineering.py    ← encode categoricals, create bands
├── evaluate.py               ← unified metrics reporting
└── trained/                  ← saved .pkl model files
```

---

### PHASE 5 — GenAI Copilot Layer

**Goal:** Plain-language insights for faculty and students using Gemini API

#### 5.1 Faculty Copilot (`genai/faculty_copilot.py`)

Prompt templates for:
- "Which students need immediate intervention?"
- "What are the top subject-level learning gaps in my class?"
- "Explain this student's risk prediction in simple terms"
- "Generate a personalized study plan for [student]"

#### 5.2 Student Copilot (`genai/student_copilot.py`)

- "What skills should I develop to become a [career]?"
- "How does my performance compare to placed students?"
- "What are my weakest subjects and how do I improve?"

#### 5.3 Grounding Strategy

- Pass student-specific data as context in every Gemini prompt
- Use structured JSON context (not raw CSV) for precision
- Output format: structured JSON → rendered in Django templates
- Rate limiting: cache GenAI responses per student per session

---

### PHASE 6 — Django Web Dashboard

**Goal:** Role-based web interface for Faculty, Students, Admins

#### 6.1 App Structure

```
dashboard/
├── campus360/              ← Django project
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── students/           ← Student profile views
│   ├── analytics/          ← Charts and dashboards (Plotly)
│   ├── predictions/        ← ML model inference
│   ├── career/             ← Career readiness + skill gaps
│   └── genai/              ← Copilot chat interface
├── templates/
│   ├── base.html
│   ├── faculty_dashboard.html
│   ├── student_profile.html
│   └── admin_dashboard.html
└── static/
    ├── css/    (Tailwind)
    └── js/
```

#### 6.2 Key Views & Pages

| Page | Role | Key Components |
|---|---|---|
| Admin Dashboard | Admin | Total students, risk distribution, placement rate |
| Faculty Dashboard | Faculty | At-risk list, class performance heatmap, GenAI copilot |
| Student Profile | Student | 360° profile, career readiness score, skill gap radar |
| Subject Analytics | Faculty | G1/G2/G3 trends, failure heatmap, subject comparison |
| Placement Analytics | Faculty/Admin | Placement funnel, salary distribution, skill correlation |
| GenAI Copilot | Faculty/Student | Chat interface powered by Gemini API |

#### 6.3 Plotly Charts Planned

- Risk distribution donut chart
- CGPA band vs placement rate bar chart
- Study hours vs exam score scatter
- Subject marks progression line chart (G1→G2→G3)
- Skill score radar chart per student
- Career readiness score gauge chart
- SHAP waterfall chart for risk explanation

---

### PHASE 7 — Dockerized Deployment

**Goal:** Fully containerized, one-command startup

#### 7.1 `docker-compose.yml`

```yaml
version: "3.9"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: campus360
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: campus360pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://admin:campus360pass@db:5432/campus360
      GEMINI_API_KEY: ${GEMINI_API_KEY}

  etl:
    build: .
    command: python etl/load_to_postgres.py
    depends_on:
      - db

volumes:
  postgres_data:
```

#### 7.2 `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
```

---

## 6. Repository Structure (Target)

```
Campus360/
├── data/
│   ├── raw/                         ← original source CSVs
│   └── processed/
│       ├── src_*.csv                ← cleaned source inputs
│       └── v5/                      ← star schema outputs ✅
│
├── etl/
│   ├── load_to_postgres.py          ← Phase 2
│   └── feature_engineering.py       ← Phase 4
│
├── analytics/
│   ├── subject_analytics.py
│   ├── risk_analytics.py
│   ├── placement_analytics.py
│   └── career_readiness.py
│
├── models/
│   ├── risk_classifier.py
│   ├── placement_predictor.py
│   ├── career_readiness_model.py
│   ├── evaluate.py
│   └── trained/
│
├── genai/
│   ├── faculty_copilot.py
│   └── student_copilot.py
│
├── dashboard/
│   ├── campus360/
│   ├── apps/
│   ├── templates/
│   └── static/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── IMPLEMENTATION_PLAN.md
└── README.md
```

---

## 7. ML Features Reference Table

| Feature | Source Table | Column | Type |
|---|---|---|---|
| CGPA Band | fact_risk_behaviour | cgpa_category | Ordinal |
| Study Hours | fact_risk_behaviour | study_hours_daily | Ordinal |
| Stress Level | fact_risk_behaviour | stress_level | Float |
| Energy Level | fact_risk_behaviour | energy_level | Float |
| Attendance Band | fact_risk_behaviour | attendance_band | Ordinal |
| Daily Productivity | fact_risk_behaviour | daily_productivity | Float |
| Sleep Hours | fact_risk_behaviour | sleep_hours | Ordinal |
| Tasks On Time | fact_risk_behaviour | tasks_on_time | Ordinal |
| Assignments On Time | fact_risk_behaviour | assignments_on_time | Ordinal |
| Programming Foundation | fact_risk_behaviour | programming_foundation | Ordinal |
| Coding Skill Score | fact_placement | coding_skill_score | Float (0-100) |
| Aptitude Score | fact_placement | aptitude_score | Float (0-100) |
| Communication Score | fact_placement | pl_communication_skill_score | Float (0-100) |
| Internships Count | fact_placement | internships_count | Int |
| Projects Count | fact_placement | projects_count | Int |
| Placement Status | fact_placement | placement_status | Binary target |
| Performance Risk Level | fact_risk_behaviour | performance_risk_level | 3-class target |

---

## 8. Career Readiness Score Formula

```python
def career_readiness_score(student):
    technical   = normalize(avg(coding_skill_score, skill_score_python,
                                skill_score_sql, skill_score_ml)) * 30
    academic    = normalize(cgpa_band_score, academic_satisfaction_score) * 20
    comm        = normalize(pl_communication_skill_score) * 15
    problem_sol = normalize(avg(logical_reasoning_score, aptitude_score)) * 15
    projects    = min(projects_count / 5, 1.0) * 10
    certs       = min(certifications_count / 3, 1.0) * 5
    interview   = normalize(mock_interview_score) * 5
    return round(technical + academic + comm + problem_sol +
                 projects + certs + interview, 1)
```

---

## 9. GenAI Prompt Template (Faculty Copilot)

```
You are an academic advisor AI for GLS University.

Student Profile:
- ID: {master_student_id}
- Program: {program_stream}, Year: {year_class}
- CGPA Band: {cgpa_category}
- Risk Level: {performance_risk_level} (model confidence: {confidence}%)
- Top Risk Factors (SHAP): {shap_factors}
- Skill Scores: Python={python_score}, SQL={sql_score}, ML={ml_score}
- Career Interest: {career_interest}
- Career Readiness Score: {career_readiness_score}/100
- Skill Gaps: {skill_gaps}

Faculty Question: {faculty_question}

Provide a concise, actionable response in 3-4 sentences.
Focus on specific, practical interventions the faculty can take this week.
```

---

## 10. Risk Levels & Intervention Mapping

| Risk Level | Count | Suggested Intervention |
|---|---|---|
| Low Risk | 176 (14.7%) | Regular check-ins |
| Moderate Risk | 572 (47.7%) | Study group assignment, mentor pairing |
| High Risk | 452 (37.7%) | Immediate 1:1 faculty meeting, counselling referral |

---

## 11. Remaining Work (Priority Order)

| Phase | Task | Priority | Est. Effort |
|---|---|---|---|
| 2 | PostgreSQL schema + load script | 🔴 High | 2–3 hours |
| 3 | Analytics engine (4 modules) | 🔴 High | 3–4 hours |
| 4 | ML models (3 models + SHAP) | 🔴 High | 4–5 hours |
| 5 | GenAI copilot (Gemini API) | 🟡 Medium | 2–3 hours |
| 6 | Django dashboard + Plotly charts | 🟡 Medium | 6–8 hours |
| 7 | Docker + docker-compose | 🟢 Low | 1–2 hours |

---

## 12. Data Quality Guarantees (Already Achieved ✅)

- ✅ 27/27 QA checks passed
- ✅ 511 nulls handled with documented, justified strategy
- ✅ `performance_risk_level` (ML target) never imputed
- ✅ GPA scales never mixed (4.0 and 10.0 kept separate)
- ✅ All probabilistic joins flagged with `is_synthetic_*`
- ✅ No fabricated student information
- ✅ Full data lineage (76 column-level entries)
- ✅ 60 dropped columns documented with reasons

---

*Last updated: 2026-09-09 | Team 60 — Rahil Nagariya & Om Patel*
