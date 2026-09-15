# KDAC-3 — Student Academic Success, Subject Performance & Career Readiness Analytics Platform

**KDAC-3** is an end-to-end Student Analytics and Early-Warning Data Warehouse platform designed to synthesize multi-source academic, behavioral, and placement records into a unified data engineering and decision-support layer.

---

## 1. Architecture & Project Layout

```text
Campus360/
│
├── data/
│   ├── raw/                           # Immutable raw departmental CSV datasets
│   │   ├── 1_student_records.csv
│   │   ├── 2_exam_marks.csv
│   │   ├── 3_attendance.csv
│   │   ├── 4_lifestyle.csv
│   │   ├── 5_skills.csv
│   │   └── 6_career_preferences.csv
│   └── processed/                     # Cleaned relational tables & stitched master dataset
│       ├── cleaned_students.csv
│       ├── cleaned_academic_records.csv
│       ├── cleaned_exam_marks.csv
│       ├── cleaned_attendance.csv
│       ├── cleaned_lifestyle.csv
│       ├── cleaned_skills.csv
│       ├── cleaned_career_preferences.csv
│       └── student_master_stitched.csv
│
├── sql/
│   ├── schema.sql                     # PostgreSQL relational DDL (7 tables, PKs, FKs, constraints)
│   └── views.sql                      # Analytical SQL views (Student 360, ML Feature views)
│
├── etl/
│   ├── __init__.py
│   ├── extract.py                     # Raw extraction & schema profiling
│   ├── transform.py                   # Type casting, anomaly handling & ID stitching
│   ├── load.py                        # Bulk PostgreSQL loader (foreign-key ordered)
│   ├── validate.py                    # Automated data quality & integrity test suite
│   ├── pipeline.py                    # Master CLI orchestrator
│   └── profiling.py                   # Deep profiling & reconciliation report generator
│
├── config/
│   ├── __init__.py
│   └── config.py                      # Centralized environment & database configuration
│
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

---

## 2. Dataset Structure

| File | Institutional Source | Original Key Column | Raw Rows | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`1_student_records.csv`** | Registrar / SIS | `student_id` | 10,080 | Core student demographics, CGPA, backlogs, failed subjects, income, enrollment date, and official `at_risk_flag`. |
| **`2_exam_marks.csv`** | Controller of Exams | `StudentID` | 10,050 | Component assessments (internal marks, assignment score, midterm), subject consistency, performance band, and future `next_semester_marks`. |
| **`3_attendance.csv`** | LMS & Biometrics | `roll_no` | 10,100 | Coursework engagement, attendance percentage, daily and weekly study hours, and sync timestamp. |
| **`4_lifestyle.csv`** | Wellness & Counseling | `student_id` | 10,060 | Sleep hours, screen time, gaming hours, stress level, burnout score, motivation, gym frequency, and wellness score. |
| **`5_skills.csv`** | Placement & Coding Cell | `STUDENT_ID` | 10,070 | Resume score, mock interview score, communication skills, aptitude, GitHub repos, and AI tool usage. |
| **`6_career_preferences.csv`** | Career Planning Office | `roll_number` | 10,050 | Hackathon participation, preferred tech domain, and primary career goal. |

---

## 3. Data-Stitching Strategy

1. **Non-Positional Key Matching**:
   - Every departmental file is joined strictly on the standardized business key `student_id`.
   - Row indices and physical file ordering are never assumed or relied upon.
2. **Key Standardization**:
   - Inconsistent identifier columns (`StudentID`, `roll_no`, `STUDENT_ID`, `roll_number`) are normalized to `student_id`.
   - All IDs are trimmed of whitespace and standardized to uppercase format (e.g. `S100000`).
3. **Deduplication Prior to Joining**:
   - Each raw source contains 50–100 duplicate submissions / re-sync rows. Deduplication on `student_id` prevents Cartesian explosion before joining.
4. **Reconciliation Statistics**:
   - **Total Master Unique IDs**: 10,000
   - **IDs Matched Across All 6 Datasets**: 10,000
   - **Match Percentage**: **100.0%** (0 unmatched students).

---

## 4. PostgreSQL Relational Schema

The data warehouse employs a normalized star-schema design centered around the `students` entity:

1. **`students`** (`student_id` PK): Core entity demographics, family income, CGPA, backlogs, and risk status.
2. **`academic_records`** (`student_id` PK/FK): Historical academic marks, consistency, and performance bands.
3. **`exam_marks`** (`student_id` PK/FK): Component exam marks and regression target (`next_semester_marks`).
4. **`attendance`** (`student_id` PK/FK): Attendance rates and study logs.
5. **`lifestyle`** (`student_id` PK/FK): Wellness, sleep, screen time, stress, and burnout metrics.
6. **`skills`** (`student_id` PK/FK): Placement interview scores, aptitude, and project counts.
7. **`career_preferences`** (`student_id` PK/FK): Hackathon counts, preferred domains, and career goals.

### Constraints & Indexes
- Foreign keys enforce `ON DELETE CASCADE` referencing `students(student_id)`.
- `CHECK` constraints enforce physical domain boundaries (e.g. `attendance_percentage BETWEEN 0.0 AND 100.0`, `cgpa BETWEEN 0.0 AND 10.0`, `sleep_hours BETWEEN 0.0 AND 24.0`).
- B-tree indexes optimize query performance on `at_risk_flag`, `performance_band`, `next_semester_marks`, and `attendance_percentage`.

---

## 5. Analytical Views Created

| View Name | Target Consumer | Description & Zero-Leakage Guarantee |
| :--- | :--- | :--- |
| **`student_360_view`** | Dashboard & Faculty Mentors | Denormalized 360-degree view joining all 7 tables for holistic reporting. |
| **`performance_features_view`** | Model 1 (Marks Regression) | Combines academic history, attendance, and lifestyle. **Strictly omits `next_semester_marks` and `performance_band`** to prevent label leakage. Separately exposes `target_next_semester_marks`. |
| **`at_risk_features_view`** | Model 2 (Risk Classification) | Combines attendance, academic fragility, and psychological stressors. **Strictly omits future exam marks** to prevent temporal leakage. Separately exposes `target_at_risk_flag`. |
| **`career_readiness_view`** | Placement Cell | Computes a normalized `composite_readiness_score` (0–100) weighting resume, interview, aptitude, projects, and hackathons. |

---

## 6. How to Configure & Run the Pipeline

### Prerequisites
- Python 3.10+ (or virtual environment)
- PostgreSQL 16 (running locally or via Docker)

### Configuration
Create `.env` based on `.env.example`:
```bash
POSTGRES_USER=campus360
POSTGRES_PASSWORD=changeme
POSTGRES_DB=campus360_warehouse
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
DATABASE_URL=postgresql://campus360:changeme@localhost:5433/campus360_warehouse
```

### Execution (One Command)
Run the entire end-to-end pipeline:
```bash
python etl/pipeline.py
```

To run individual pipeline stages:
```bash
# Profile raw data & ID reconciliation
python etl/profiling.py

# Extract raw datasets
python etl/extract.py

# Clean, transform, and stitch
python etl/transform.py

# Load into PostgreSQL & build views
python etl/load.py

# Execute automated quality validation tests
python etl/validate.py
```

---

## 7. Data Quality Validation Results

Running `python etl/validate.py` executes automated tests across 5 quality dimensions:

1. **Row Count & Uniqueness**: Exactly **10,000 distinct students** loaded into every warehouse table.
2. **Referential Integrity**: **0 orphaned foreign keys** across all child tables.
3. **Domain Constraints**: **0 boundary violations** (CGPA, attendance, percentages, marks, and sleep hours all within valid ranges).
4. **Null Checks**: **0 unexpected nulls** in primary or foreign keys.
5. **Analytical Views**: All 4 views query 10,000 rows without execution errors.
6. **ETL Idempotency**: Running `pipeline.py` multiple times executes safely without duplicating rows.
