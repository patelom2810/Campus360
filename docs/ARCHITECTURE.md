# Campus360: Architecture & Data Engineering Master Document
### Multi-Source Student Academic Success, Subject Performance & Career Readiness Analytics Platform
**Project Name:** Campus360 | **Problem Code:** KDAC-3 (KENEXA AI Hackathon)  
**Authors:** Om Patel & Rahil Nagariya (Team ID: 60)  
**Status:** Completed & Validated

---

## 1. Data Stitching & Warehouse Engineering

### Executive Overview & Problem Context

In higher education institutions, student intelligence is fragmented across incompatible databases:
- **Academic Registrars / ERP:** Subject grades, mid-term evaluations, attendance logs, and pass/fail statuses.
- **Placement & Career Cells:** Corporate offers, salary packages, internships, coding test ratings, and backlogs.
- **Counseling & Student Wellness:** Daily sleep hours, screen time, stress levels, physical activity, and burnout markers.

None of these databases share a universal student identity key. Traditional random joins produce nonsensical synthetic records (e.g. a 9.5 CGPA student failing primary math, or an insomniac with zero stress and top-tier placement).

**Objective:**  
Ingest 6 independent Indian student datasets, clean and normalize all attributes, establish an institutional master identity (`STU00001`–`STU25000`), perform **Attribute-Based Statistical Similarity Matching**, and construct a production-ready **Star Schema Data Warehouse** accompanied by comprehensive data lineage.

---

### Ingested Datasets Summary

All 6 canonical raw datasets are preserved untouched in `data/raw/`:

| # | Dataset Key | Canonical Filename | Source / Author | Raw Rows | Processed Rows | Domain Coverage | Native Academic Metric |
|---|---|---|---|---|---|---|---|
| **1** | `shambhuraje` | `shambhuraje_placement_career_2026.csv` | Shambhuraje (2026) | 25,000 | 25,000 | **MASTER ANCHOR SPINE**: Academics, LeetCode/GitHub coding profiles, internships, lifestyle wellness, AI tools, placement | `cgpa` (5.0 – 10.0) |
| **2** | `kundan` | `kundan_student_performance.csv` | Kundan (India) | 25,000 | 15,000 | Secondary academics (Math, Science, English), school type, travel time, study methods | `overall_score` (0 – 100) |
| **3** | `sakharebharat` | `sakharebharat_indian_placement_2025.csv` | Sakhare Bharat (2025) | 12,000 | 12,000 | Engineering placement, coding/communication skills, aptitude, project count, salary packages | `cgpa` (5.5 – 9.8) |
| **4** | `suvidya` | `suvidya_student_performance.csv` | Suvidya (India) | 5,000 | 5,000 | Intermediate academic marks (Math, Science, English), attendance, parental education, pass/fail | `final_percentage` (36% – 98%) |
| **5** | `sehaj` | `sehaj_student_lifestyle.csv` | Sehaj Sharma (Kaggle) | 2,000 | 2,000 | Student lifestyle, daily physical activity, social hours, sleep duration, stress levels | `gpa` (2.24 – 4.0) |
| **6** | `navinpatidar` | `navinpatidar_indian_placement.csv` | Navin Patidar (India) | 1,000 | 1,000 | Campus placement, corporate recruiters, job roles, packages in INR | `salary_inr` (₹301k – ₹1,198k) |

*Note on Sehaj Dataset:* Recovered directly from Git commit history (`f8e444f5...`) and verified to match Sehaj Sharma's Kaggle benchmark.  
*Note on Kundan Dataset:* Raw file contained 10,000 exact duplicate records, which were pruned in `clean.py` down to the 15,000 unique records specified in the blueprint.

---

### Repository Architecture & Layout

The project follows a clean decoupled pipeline architecture:

```
Campus360/
│
├── venv/                              # Python 3.14 Virtual Environment (OpenMP / libomp configured)
│
├── data/
│   ├── raw/                           # 6 untouched original CSV files
│   │   ├── suvidya_student_performance.csv
│   │   ├── kundan_student_performance.csv
│   │   ├── sehaj_student_lifestyle.csv
│   │   ├── navinpatidar_indian_placement.csv
│   │   ├── sakharebharat_indian_placement_2025.csv
│   │   └── shambhuraje_placement_career_2026.csv
│   ├── interim/                       # Cleaned, imputed, deduplicated CSVs (0 nulls remaining)
│   │   ├── suvidya_clean.csv
│   │   ├── kundan_clean.csv
│   │   ├── sehaj_clean.csv
│   │   ├── navinpatidar_clean.csv
│   │   ├── sakharebharat_clean.csv
│   │   └── shambhuraje_clean.csv
│   └── processed/                     # Production Data Warehouse Layer (Star Schema + PostgreSQL / SQLite)
│       ├── student_master_wide.csv    # Unified 25,000-row master wide table (112 columns after PII drop)
│       ├── dim_student.csv            # Student demographic & institutional dimension (25,000 rows)
│       ├── fact_performance.csv       # Long-format subject marks & attendance fact table (105,000 rows)
│       ├── fact_lifestyle.csv         # Habits, sleep, stress & wellness fact table (25,000 rows)
│       ├── fact_career.csv            # Skills, backlogs, placement & salary fact table (25,000 rows)
│       ├── model1_performance_train.csv
│       ├── model1_performance_test.csv
│       ├── model2_atrisk_train.csv
│       ├── model2_atrisk_test.csv
│       └── warehouse.db               # Embedded SQLite database for local fallback
│
├── src/
│   ├── etl/                           # Modular Data Engineering & Stitching Pipeline
│   │   ├── __init__.py
│   │   ├── extract.py                 # Ingests raw data and profiles shapes, nulls, and scales
│   │   ├── clean.py                   # Standardizes column names, imputes nulls, and clips ranges
│   │   ├── stitch.py                  # Implements attribute-based matching onto anchor spine
│   │   ├── load.py                    # Star schema PostgreSQL loader & SQLite fallback
│   │   ├── fix_and_prepare.py         # PII drop, casing standardization, at_risk_flag & splits
│   │   └── run_pipeline.py            # Master CLI runner executing Stages 1-4 end-to-end
│   │
│   │   ├── train_performance_model.py # Marks prediction regressor (Model 1)
│   │   └── train_atrisk_model.py      # At-risk early detection classifier (Model 2)
│   │   # Note: Career Guidance is an analytical 6-pillar composite scoring engine (_CAREER_WEIGHTS)
│   │
│   ├── genai/                         # GenAI Copilot Layer
│   │   └── insights.py                # Plain-language student & teacher guidance
│   │
│   ├── dashboard/                     # Web Dashboard
│   │   └── app.py                     # Streamlit multi-tab warehouse explorer
│   │
│   └── api/                           # Backend
│       └── main.py                    # FastAPI application
│
├── notebooks/
│   └── eda.ipynb                      # Exploratory data analysis Jupyter notebook
│
├── docker/
│   ├── Dockerfile.api                 # API container definition
│   └── Dockerfile.dashboard           # Streamlit dashboard container definition
│
├── tests/
│   ├── __init__.py
│   ├── test_etl_pipeline.py           # 5 automated integration & data quality tests
│   ├── test_fix_and_prepare.py        # 5 data quality, leakage & split integrity tests
│   └── test_postgres_migration.py     # 6 database migration & fallback parity tests
│
├── requirements.txt                   # Frozen production dependencies
├── .env.example                       # Environment configuration template
├── .gitignore                         # Python, venv, database, and OS cache exclusions
├── README.md                          # Quick start and platform documentation
└── docs/
    ├── ARCHITECTURE.md                # Consolidated architecture, stitching, lineage & label engineering
    └── DEPLOYMENT.md                  # Deployment, container orchestration, and database migration
```

---

### Environment & Virtual Environment Setup

1. **Virtual Environment Creation:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   ```
2. **Dependency Installation:**
   All 16 production libraries from `requirements.txt` installed into `venv/`:
   - **Data Processing:** `pandas` (3.0.5), `numpy` (2.5.3), `openpyxl`
   - **Machine Learning:** `scikit-learn` (1.9.0), `xgboost` (3.4.1), `scipy`
   - **Visualizations:** `matplotlib`, `seaborn`, `plotly`
   - **Dashboard & API:** `streamlit` (1.63.0), `fastapi` (0.141.1), `uvicorn[standard]`
   - **Databases:** `sqlalchemy` (2.0.52), `psycopg2-binary`
   - **GenAI & Notebooks:** `anthropic` (1.4.0), `jupyter`, `python-dotenv`
3. **macOS System Runtime Optimization:**
   Configured Homebrew `libomp` (`brew install libomp`) to enable native OpenMP multi-threading acceleration for `xgboost` on macOS ARM64.

---

### End-to-End ETL Pipeline Implementation

```mermaid
flowchart TD
    subgraph S1["Stage 1: Extract (extract.py)"]
        Raw["6 Raw CSVs in data/raw/"] --> Profile["Profile dtypes, nulls, scales & naming"]
    end

    subgraph S2["Stage 2: Clean (clean.py)"]
        Profile --> Standardize["snake_case renaming"]
        Standardize --> Impute["Median numeric / Mode categorical imputation"]
        Impute --> Clip["Clip attendance [0-100%], marks [0-100], GPA [0-10]"]
        Clip --> Deduplicate["Deduplicate (Kundan 25k -> 15k unique)"]
        Deduplicate --> Interim["Save data/interim/*_clean.csv (0 nulls)"]
    end

    subgraph S3["Stage 3: Stitch (stitch.py)"]
        Interim --> Anchor["Anchor: shambhuraje (STU00001 - STU25000)"]
        Anchor --> Banding["Attribute Banding: Tertiles (Low/Med/High) + Gender + Branch"]
        Banding --> Matching["Sample without replacement (max 1 row per anchor student)"]
        Matching --> Wide["Left join with source prefixes -> data/processed/student_master_wide.csv"]
    end

    subgraph S4["Stage 4: Load (load.py)"]
        Wide --> Dim["dim_student.csv (25,000 rows)"]
        Wide --> FactP["fact_performance.csv (105,000 rows)"]
        Wide --> FactL["fact_lifestyle.csv (25,000 rows)"]
        Wide --> FactC["fact_career.csv (25,000 rows)"]
        Dim & FactP & FactL & FactC --> Postgres["PostgreSQL / SQLite fallback"]
    end
```

#### Stage 1: Extraction & Profiling (`src/etl/extract.py`)
- Verified existence and accessibility of all 6 raw files.
- Highlighted unit and scale discrepancies:
  - **GPA vs CGPA:** Sehaj on a 4.0 scale (2.24–4.0), Sakhare and Shambhuraje on a 10.0 scale (5.0–10.0).
  - **Salary Packages:** Navinpatidar in annual INR (₹301k–₹1,198k), Sakhare and Shambhuraje in Lakhs Per Annum (LPA).
  - **Casing:** Heterogeneous PascalCase (`Student_ID`, `Graduation Year`) vs snake_case (`student_id`, `cgpa`).

#### Stage 2: Independent Dataset Cleaning (`src/etl/clean.py`)
- Standardized all column names into clean, lowercase `snake_case`.
- Imputed missing values:
  - `shambhuraje`: Imputed `github_repos`, `sleep_hours`, `mock_interview_score` with numeric medians; imputed unplaced students' `company_type` and `work_mode` as `"Not Placed"` / `"None"`.
  - `sakharebharat`: Imputed `company_type` as `"Not Placed"` for students with `placed == 0`.
- Range clipping:
  - `attendance_percentage` clipped to `[0.0, 100.0]`.
  - Academic marks clipped to `[0.0, 100.0]`.
  - CGPA clipped to `[0.0, 10.0]` and GPA to `[0.0, 4.0]`.
- Output: 6 interim tables saved to `data/interim/*_clean.csv` with **zero remaining nulls**.

#### Stage 3: Attribute-Based Similarity Matching (`src/etl/stitch.py`)
- **Master Anchor Spine:** Initialized `shambhuraje_clean.csv` as the foundation (25,000 records) and generated immutable institutional keys: `STU00001` through `STU25000`.
- **2-Tier Attribute Banding Algorithm:**
  1. **Performance Tertiles:** Partitioned each dataset into `Low` (bottom 33%), `Medium` (middle 33%), and `High` (top 33%) bands based on its own native academic metric.
  2. **Demographic & Branch Clustering:** Clustered branches into `Tech` (CS, IT, AI, DS), `Core_Engineering` (Mechanical, Civil, Electrical, Electronics), and `General`. Mapped reported genders (`Male`, `Female`, `Other`).
  3. **Multi-Pass Assignment Without Replacement:**
     - *Pass 1 (Strict):* Matched within `(Performance Band + Demographics)`.
     - *Pass 2 (Band-Preserving Overflow):* Matched any sub-demographic overflow strictly within the **same performance band**, guaranteeing that a low-performing student in high school never pairs with an elite collegiate performer.
  4. **Constraint Enforcement:** Every anchor student receives **at most one** row from each secondary source. Unmatched students have `NULL` values and explicit binary match flags (`has_suvidya_match`, `has_kundan_match`, etc.).
- **Wide Master Table:** Left-joined all sources with explicit column prefixes (`anchor_`, `suvidya_`, `kundan_`, `sehaj_`, `navin_`, `sakhare_`) to prevent namespace collisions. Saved as `data/processed/student_master_wide.csv` (25,000 rows × 113 columns).

#### Stage 4: Star Schema Data Warehouse Generation (`src/etl/load.py`)
Decomposed the wide table into four star schema relational tables:

1. **`dim_student.csv` (25,000 rows × 9 columns):**
   - Universal Primary Key: `student_id` (`STU00001`–`STU25000`)
   - Attributes: `gender`, `age`, `stream_branch`, `degree`, `college_tier`, `city_tier`, `state`, `family_income_lpa`.
2. **`fact_performance.csv` (105,000 rows × 8 columns):**
   - Normalized long-format fact table containing subject-level granularity.
   - 20,000 records from Suvidya (Math, Science, English, Overall).
   - 60,000 records from Kundan (Math, Science, English, Overall).
   - 25,000 records from Anchor (Cumulative Degree CGPA).
   - Columns: `student_id`, `source`, `assessment_term`, `subject`, `marks`, `max_marks`, `attendance_pct`, `grade_or_status`.
3. **`fact_lifestyle.csv` (25,000 rows × 12 columns):**
   - Primary Key: `student_id`
   - Attributes: `sleep_hours`, `screen_time_hours`, `gaming_hours`, `study_hours_daily`, `stress_level`, `burnout_score`, `gym_frequency_per_week`, `motivation_level`, `physical_activity_hours_sehaj`, `stress_level_sehaj`.
   - Derived KPI: `lifestyle_risk_flag` (`High Risk` if sleep < 5.0h, stress > 75, or burnout > 75; else `Normal`).
4. **`fact_career.csv` (25,000 rows × 16 columns):**
   - Primary Key: `student_id`
   - Attributes: `cgpa`, `backlogs`, `internships`, `dsa_problems_solved`, `github_repos`, `coding_skills_sakhare`, `communication_skills`, `aptitude_score`, `mock_interview_score`, `placement_status`, `company_type`, `work_mode`, `salary_lpa`, `offer_count`, `layoffs_risk_score`.
5. **Database Export:**
   - Automatically loaded into PostgreSQL with explicit DDL, primary keys, and foreign keys. Maintained local `warehouse.db` (SQLite) backup for demo safety.

#### Stage 5: Master Orchestrator (`src/etl/run_pipeline.py`)
Provides single-command end-to-end pipeline execution:
```bash
python3 -m src.etl.run_pipeline
```
**Runtime:** Entire pipeline runs from raw CSVs to warehouse in **~5.5 seconds**.

---

### Verification, Validation & Data Quality Assurance

#### A. Empirical Statistical Validation (Correlation Preservation)
Pearson correlation ($r$) between Anchor CGPA and secondary datasets confirms strong, realistic positive relationships across all matched dimensions:

| Comparison Metric | Source Dataset | Rows Evaluated | Pearson Correlation ($r$) | Statistical Significance |
|---|---|---|---|---|
| **Anchor CGPA vs. Sakhare CGPA** | Sakharebharat (2025) | 12,000 | **+0.842** | $p < 0.0001$ (Very Strong) |
| **Anchor CGPA vs. Navin Package** | Navinpatidar Placement | 1,000 | **+0.853** | $p < 0.0001$ (Very Strong) |
| **Anchor CGPA vs. Kundan Score** | Kundan Performance | 15,000 | **+0.824** | $p < 0.0001$ (Very Strong) |
| **Anchor CGPA vs. Suvidya %** | Suvidya Performance | 5,000 | **+0.807** | $p < 0.0001$ (Very Strong) |
| **Anchor CGPA vs. Sehaj GPA** | Sehaj Lifestyle | 2,000 | **+0.805** | $p < 0.0001$ (Very Strong) |

#### B. Automated Unit & Integration Test Suite (`tests/test_etl_pipeline.py`)
- `test_raw_files_exist`: Confirmed presence of all 6 raw CSV files.
- `test_interim_files_clean`: Confirmed interim CSVs are non-empty with clean lowercase snake_case schema.
- `test_wide_master_integrity`: Verified 25,000 rows with strictly unique IDs `STU00001` through `STU25000`.
- `test_star_schema_relationships`: Validated table row counts and verified that all foreign keys in fact tables cleanly reference `dim_student`.
- `test_statistical_realism`: Validated that academic correlations across joined tables exceed $r > 0.70$.

---

## 2. Data Lineage & Matching Architecture

### Executive Summary
In higher education institutions, student data is notoriously fragmented across disconnected silos:
- **ERP / Academic Registrars:** Subject exam marks, attendance records, and term pass/fail flags.
- **Placement & Corporate Relations Cells:** Off-campus/on-campus offers, company packages, internship history, and coding profiles.
- **Wellness & Student Affairs Offices:** Sleep patterns, stress levels, mental health indicators, and lifestyle surveys.

To build a **360° Student Intelligence Platform**, this pipeline stitches **6 independent real-world Indian student datasets** into a coherent data warehouse using **Attribute-Based Probabilistic Similarity Matching**. Rather than joining randomly or simulating ungrounded synthetic students, this methodology preserves true multivariate distributions, ensuring correlations between academic ability, lifestyle habits, and placement outcomes remain statistically realistic.

---

### Anchor Selection & Institutional Identity Spine
- **Anchor Dataset:** `shambhuraje_placement_career_2026.csv` was selected as the **Golden Record (Spine)** because:
  1. It is the largest single dataset (25,000 records).
  2. It contains the widest feature breadth (44 attributes covering academics, coding profiles, lifestyle wellness, AI-tool usage, and placement results).
  3. It spans realistic Indian collegiate demographics across diverse branches (Computer Science, AI & DS, IT, Electronics, Mechanical, Civil) and states.
- **Institutional Master ID (`student_id`):**
  Each row in the anchor dataset is assigned an immutable, standard primary key: `STU00001` through `STU25000`. This key serves as the universal foreign key across all dimension and fact tables in the star schema.

---

### Synthetic vs. Original Field Audit

| Table | Column Name | Origin Source | Type | Transformation / Description |
|---|---|---|---|---|
| **dim_student** | `student_id` | Pipeline generated | **Synthetic PK** | Format `STU00001` - `STU25000` |
| **dim_student** | `gender`, `age` | `shambhuraje` | **Original** | Standardized casing |
| **dim_student** | `stream_branch`, `degree` | `shambhuraje` | **Original** | Engineering branch and degree programme |
| **dim_student** | `college_tier`, `city_tier`, `state` | `shambhuraje` | **Original** | Institutional classification |
| **dim_student** | `family_income_lpa` | `shambhuraje` | **Original** | Annual family income in LPA |
| **fact_performance** | `subject` | `suvidya`, `kundan`, `shambhuraje` | **Transformed** | Melted long-format subject name (Math, Science, English, Degree CGPA) |
| **fact_performance** | `marks` | `suvidya`, `kundan`, `shambhuraje` | **Original** | Exam score on respective subject scale |
| **fact_performance** | `max_marks` | System metadata | **Derived** | Assessment scale denominator (100.0 for school/term, 10.0 for CGPA) |
| **fact_performance** | `attendance_pct` | `suvidya`, `kundan`, `shambhuraje` | **Original** | Clipped to valid range [0.0, 100.0] |
| **fact_lifestyle** | `sleep_hours` | `shambhuraje` | **Original** | Imputed median on 500 missing values, clipped |
| **fact_lifestyle** | `screen_time_hours`, `gaming_hours` | `shambhuraje` | **Original** | Daily hours recorded in survey |
| **fact_lifestyle** | `stress_level`, `burnout_score` | `shambhuraje` | **Original** | Normalized 0-100 wellness index |
| **fact_lifestyle** | `physical_activity_hours_sehaj` | `sehaj` | **Original** | Hours per day from matched Sehaj survey |
| **fact_lifestyle** | `lifestyle_risk_flag` | Pipeline rule engine | **Derived** | `High Risk` if sleep < 5h or stress > 75 or burnout > 75; else `Normal` |
| **fact_career** | `cgpa`, `backlogs` | `shambhuraje` | **Original** | Academic career prerequisites |
| **fact_career** | `internships`, `dsa_problems_solved` | `shambhuraje` | **Original** | Technical preparation milestones |
| **fact_career** | `coding_skills_sakhare` | `sakharebharat` | **Original** | 1-10 skill rating from matched 2025 placement survey |
| **fact_career** | `salary_lpa` | `shambhuraje` | **Original** | Annual package offered (LPA) |
| **fact_career** | `placement_status`, `company_type` | `shambhuraje` | **Original** | Employment result and organization profile |
| **fact_career** | `layoffs_risk_score` | `shambhuraje` | **Original** | Predictive risk indicator for career coaching |

---

### Key Data Engineering Assumptions

1. **Deduplication:**
   `kundan_student_performance.csv` contained 10,000 exact duplicates in its raw download. These were safely pruned in `clean.py` down to the 15,000 unique records described in the project blueprint.
2. **Missingness Preservation:**
   Because anchor students outnumber secondary datasets (e.g. 1,000 Navinpatidar rows vs 25,000 anchor students), we deliberately do **not** hallucinate synthetic records to fill remaining slots. Unmatched rows naturally have `NULL` values and are tracked with `has_*_match` indicator flags, maintaining scientific honesty.
3. **Scale Coexistence:**
   GPA on the 4.0 scale (`sehaj`) and CGPA on the 10.0 scale (`sakhare`, `shambhuraje`) are retained on their native scales in their respective source columns and clearly labeled with `max_marks` metadata in `fact_performance.csv` to avoid scale confusion.
4. **Reproducibility:**
   All stochastic matching steps use fixed random seeds (`random_state = 42, 101, 202, 303, 404`). Re-running the pipeline yields bit-for-bit identical tables every time.

---

## 3. Label Engineering: `at_risk_flag`

### Problem Context & Target Invalidation
- **`anchor_placement_status` Invalidation:** Raw placement status exhibits extreme class imbalance (98.4% "Placed" vs 1.6% "Not Placed"). A model trained on this target achieves 98.4% dummy accuracy by predicting majority class on all instances, failing to provide actionable predictive utility.
- **`navin_placement_status` Invalidation:** The Navin Patidar source dataset records exclusively placed students (100% positive class, zero negative examples), making it mathematically impossible to train a binary classifier.

### Engineered Composite Definition
To construct a robust institutional early warning signal across all 25,000 students, an academic and operational composite metric was engineered:

```python
at_risk_flag = 1 if (
    anchor_backlog_history >= 1
    OR anchor_attendance_percentage < 55
    OR anchor_cgpa < 5.5
) else 0
```

### Threshold Calibration & Distribution Progression
1. **Baseline Evaluation:**
   - Condition: `(anchor_backlog_history >= 1) OR (anchor_attendance_percentage < 65) OR (anchor_cgpa < 6.0)`
   - Positive Class: **39.77%** (9,943 students)
   - Negative Class: **60.23%** (15,057 students)
   - Analysis: Because `anchor_backlog_history >= 1` alone accounts for 30.39% of the student population, combining with attendance < 65% and CGPA < 6.0 yields ~39.77% positive class, slightly exceeding the 35% ceiling.

2. **Locked Calibrated Thresholds:**
   - Condition: `(anchor_backlog_history >= 1) OR (anchor_attendance_percentage < 55) OR (anchor_cgpa < 5.5)`
   - Positive Class: **31.89%** (7,973 students)
   - Negative Class: **68.11%** (17,027 students)
   - Ratio: **68.1% / 31.9%**
   - Compliance: Meets the target window of **65/35 to 80/20** class balance (positive class between 20% and 35%).

### Academic Rationale
- **Backlogs (`>= 1`):** Having an active or historical backlog represents a direct credit deficit requiring remediation before graduation.
- **Severe Attendance Deficit (`< 55%`):** Falls well below statutory UGC/AICTE minimum attendance thresholds (75%), triggering institutional examination debarment.
- **Critical Academic Risk (`< 5.5 CGPA`):** Places the student in the bottom ~1.5% percentile of institutional GPA, severely jeopardizing campus placement eligibility.

### Model 2 Leakage Prevention
Because `at_risk_flag` is built directly from `anchor_backlog_history`, `anchor_attendance_percentage`, and `anchor_cgpa`, these three columns are **strictly excluded** from Model 2 training features. Model 2 is trained exclusively on independent lifestyle and behavioral attributes:
- `anchor_sleep_hours`, `anchor_screen_time`, `anchor_gaming_hours`, `anchor_stress_level`, `anchor_burnout_score`, `anchor_study_hours_daily`, `anchor_self_learning_hours`, `anchor_motivation_level`, `anchor_adaptability_score`, `anchor_gym_frequency`, `anchor_family_income_lpa`.

Label Integrity Sanity Check: A model trained with anchor_backlog_history, anchor_attendance_percentage, and anchor_cgpa included as features achieves near-perfect separation (ROC AUC ≈ 1.0) when predicting at_risk_flag. This is EXPECTED and NOT a predictive finding — at_risk_flag is deterministically defined as a threshold function of these exact three columns (see label_engineering section above), so this result only confirms the label was constructed correctly, i.e. it recovers from its own defining formula. It is reported here as an engineering validation step, not as evidence that academic features 'predict' risk in any generalizable sense.

### Non-Circular Ceiling Test (`suvidya_pass_fail`)
To evaluate whether academic context provides predictive uplift beyond lifestyle attributes without circular label reconstruction, two models were evaluated against an independent external ground-truth risk proxy, `suvidya_pass_fail` (mapped to 1=Fail, 0=Pass), on the $N=5,000$ Suvidya-matched subcohort (`has_suvidya_match == 1`):
- **Model A (Lifestyle Only — 23 features):** ROC AUC **0.6065**, Recall **0.1698**, Precision **0.1324**.
- **Model B (Lifestyle + Academic — 26 features):** ROC AUC **0.8728**, Recall **0.6792**, Precision **0.1773**.

### Confound Disclosure — Stitching-Induced Correlation
The lifestyle-vs-academic comparison on suvidya_pass_fail (Section 3) shows an apparent uplift when academic features are added (ROC AUC 0.6065 -> 0.8728). However, this result should be interpreted with caution: anchor_cgpa was also a primary matching key used during attribute-based dataset stitching (see Data Stitching section) to assign Suvidya records to anchor students, producing a validated correlation of r=0.8072 between anchor_cgpa and suvidya_final_percentage on the matched subset. Consistent with this, anchor_cgpa alone carries 59.32% of the academic model's feature importance. This means part of the observed 'uplift' likely reflects the stitching methodology's own matching logic rather than a purely independent, real-world relationship between academic records and risk. This is a known and disclosed limitation of building a data warehouse from independently-sourced public datasets via synthetic matching, rather than a single institution's naturally-joined real records. We expect this confound to resolve once the platform is deployed against a real institution's data, where academic and lifestyle records for the same student arrive already linked, with no matching-induced correlation to account for.

---

## 4. PII Removal Audit

- **Dropped Columns:** `navin_name` and `navin_email`.
- **Row count before PII removal:** **25,000**
- **Row count after PII removal:** **25,000**
- **Net row loss:** **0 rows** (100% data preservation).
- **Secondary verification:** Automated regex and schema scans confirmed zero remaining columns contain free-text names, phone numbers, or email addresses.
- **Categorical Normalization:**
  - `kundan_final_grade`: Standardized lowercase single letters `['a', 'b', 'c', 'd', 'e', 'f']` to uppercase `['A', 'B', 'C', 'D', 'E', 'F']`.
  - Secondary attributes (`school_type`, `parent_education`, `study_method`) normalized to Title Case while protecting uppercase acronyms (`PhD`).

---

# Part II: End-to-End System Architecture, Topology & Mermaid Data Flows

## 1. Executive Architecture Overview

Campus360 is a decoupled, modular, and containerized higher-education intelligence platform. It reconciles disparate student datasets across academic, lifestyle, coding, and career domains into a unified star-schema data warehouse, executes machine learning inference with strict anti-leakage guarantees, computes discipline-adaptive career readiness, and provides plain-language advisory narratives through a resilient GenAI pipeline.

```mermaid
flowchart TD
    subgraph DataSources["1. Raw Multi-Source Data Tier"]
        R1["shambhuraje (25k rows, Anchor Spine)"]
        R2["kundan (15k unique rows, Academics)"]
        R3["sakharebharat (12k rows, Placement & Skills)"]
        R4["suvidya (5k rows, Exam Marks & Pass/Fail)"]
        R5["sehaj (2k rows, Lifestyle & Habits)"]
        R6["navinpatidar (1k rows, Recruiter Packages)"]
    end

    subgraph ETLPipeline["2. Data Engineering & Stitching Pipeline"]
        E1["Extract & Schema Profiling"]
        E2["Clean, Deduplicate & Clip Ranges"]
        E3["Attribute-Based Statistical Stitching"]
        E4["PII Purge (navin_name, navin_email dropped)"]
        E5["Label Engineering (at_risk_flag)"]
        E6["Feature Engineering (5 interaction terms)"]
    end

    subgraph DataWarehouse["3. Star Schema Data Warehouse"]
        D1[("dim_student: 25,000 rows")]
        F1[("fact_performance: 105,000 rows")]
        F2[("fact_lifestyle: 25,000 rows")]
        F3[("fact_career: 25,000 rows")]
        SW[("student_master_wide.csv: 112 columns")]
    end

    subgraph MLTier["4. Machine Learning & Predictive Engines"]
        M1["Model 1: Gradient Boosting Regressor\n(Predicts CGPA, R²=0.2096, 28 features)"]
        M2["Model 2: Balanced Logistic Regression\n(Predicts at_risk_flag, Recall=0.5022, 23 features)"]
        LK["Strict Anti-Leakage Isolation Barrier\n(Excludes attendance, backlogs, cgpa from M2)"]
    end

    subgraph AnalyticsEngine["5. Domain Logic & Assessment Engines"]
        CR["Branch-Adaptive Career Engine\n(CS vs Non-CS Dynamic Weights)"]
        WI["Real-time What-If Simulator"]
        BYOD["BYOD Assessment Engine (Stateless)\n- Option 1: CSV Match & Confirm\n- Option 2: Multi-CSV Stitching\n- Option 3: Chatbot Guided\n- Option 4: Direct Form"]
    end

    subgraph GenAITier["6. Resilient GenAI Copilot (Gemini API)"]
        GA["Google Gemini Pipeline (gemini-3.5-flash-lite)"]
        FB["Deterministic Statistical Fallback Engine\n(Activates when Token Unset, 429 Quota, or 503)"]
        MC["SHA-256 In-Memory Cache"]
    end

    subgraph APITier["7. Backend Services (FastAPI)"]
        API["FastAPI App (uvicorn, port 8000)\n- RESTful Endpoints\n- Dynamic Population Benchmarking\n- Zero DB Mutation Guarantee"]
    end

    subgraph PresentationTier["8. Web Presentation Tier (Port 8501)"]
        UI1["Analytics Dashboard (index.html, app.js)"]
        UI2["BYOD Assessment Studio (assess.html, assess.js)"]
        UI3["Architecture Reference (arch.html)"]
        UI4["Streamlit Explorer (app.py)"]
    end

    DataSources --> ETLPipeline
    ETLPipeline --> DataWarehouse
    DataWarehouse --> MLTier
    DataWarehouse --> AnalyticsEngine
    MLTier --> APITier
    AnalyticsEngine --> APITier
    DataWarehouse --> APITier
    APITier --> GenAITier
    GA --> APITier
    FB --> APITier
    APITier --> PresentationTier
```

---

## 2. Data Engineering & Stitching Flow

In higher education, student intelligence is siloed. No universal student identity exists across independent surveys and legacy ERPs. Campus360 stitches 6 independent raw datasets onto an anchor spine using **Attribute-Based Statistical Similarity Matching** while preserving native scales, zero nulls after imputation, and full lineage disclosure.

```mermaid
sequenceDiagram
    autonumber
    participant Raw as Raw Data Tier (6 CSVs)
    participant Clean as Cleaning & Deduplication (clean.py)
    participant Stitch as Stitching Engine (stitch.py)
    participant Prep as Feature & Label Prep (fix_and_prepare.py)
    participant Loader as Star Schema Loader (load.py)
    participant DB as PostgreSQL / SQLite Warehouse

    Raw->>Clean: Ingest raw files (70,000 raw rows)
    Note over Clean: Prunes 10,000 exact duplicates from Kundan.<br/>Standardizes casing, clips ranges, handles missingness.
    Clean->>Stitch: 6 cleaned interim CSVs (0 nulls)
    
    Note over Stitch: Shambhuraje acts as Master Anchor Spine (STU00001 - STU25000).<br/>Kundan, Sakhare, Suvidya, Sehaj, and Navin stitched via<br/>CGPA quantiles, tier/branch attributes, and correlation keys.
    Stitch->>Prep: student_master_wide.csv (25,000 rows)
    
    Note over Prep: 1. Drops PII (navin_name, navin_email).<br/>2. Computes at_risk_flag (calibrated composite, 31.89% positive).<br/>3. Computes 5 interaction features.<br/>4. Generates stratified 80/20 train/test splits.
    Prep->>Loader: Verified tables & train/test splits
    Loader->>DB: Populate dim_student (25k), fact_performance (105k),<br/>fact_lifestyle (25k), fact_career (25k)
```

### Data Lineage & Volume Audit

| Dataset Key | Canonical Raw Filename | Raw Rows | Processed Rows | Match Criteria / Target Dimension | Lineage Flag |
|---|---|---|---|---|---|
| `shambhuraje` | `shambhuraje_placement_career_2026.csv` | 25,000 | 25,000 | **Master Anchor Spine** (`STU00001`–`STU25000`) | Core Spine |
| `kundan` | `kundan_student_performance.csv` | 25,000 | 15,000 | Secondary academics matched on CGPA quantile & branch | `has_kundan_match` |
| `sakharebharat` | `sakharebharat_indian_placement_2025.csv` | 12,000 | 12,000 | Placement & skills matched on engineering branch & tier | `has_sakhare_match` |
| `suvidya` | `suvidya_student_performance.csv` | 5,000 | 5,000 | Intermediate marks matched on CGPA correlation ($r=0.807$) | `has_suvidya_match` |
| `sehaj` | `sehaj_student_lifestyle.csv` | 2,000 | 2,000 | Lifestyle & physical habits matched on scaled GPA | `has_sehaj_match` |
| `navinpatidar` | `navinpatidar_indian_placement.csv` | 1,000 | 1,000 | Top recruiter packages matched on high-tier academic band | `has_navin_match` |

---

## 3. Star Schema Warehouse Entity-Relationship Architecture

The production warehouse resides in **PostgreSQL 16** (`campus360_warehouse`) with automatic local fallback to embedded **SQLite** (`data/processed/warehouse.db`).

```mermaid
erDiagram
    dim_student ||--o{ fact_performance : "has academic records"
    dim_student ||--|| fact_lifestyle : "tracks lifestyle habits"
    dim_student ||--|| fact_career : "records career readiness"

    dim_student {
        string student_id PK "STU00001 - STU25000"
        string branch "Engineering discipline"
        int college_tier "1 = Tier 1, 2 = Tier 2, 3 = Tier 3"
        string gender "Gender demographic"
        string school_type "Government / Private"
        string parent_education "Parent highest education"
        boolean has_kundan_match "Lineage flag"
        boolean has_sakhare_match "Lineage flag"
        boolean has_suvidya_match "Lineage flag"
        boolean has_sehaj_match "Lineage flag"
        boolean has_navin_match "Lineage flag"
    }

    fact_performance {
        int performance_id PK "Auto-increment primary key"
        string student_id FK "References dim_student"
        string source "shambhuraje, kundan, or suvidya"
        string subject "Subject name or exam stage"
        float marks "Normalized or native marks"
        float max_marks "Maximum scale reference"
        float attendance "Subject attendance percentage"
    }

    fact_lifestyle {
        string student_id PK, FK "References dim_student"
        float sleep_hours "Daily sleep hours"
        float screen_time "Daily non-study screen hours"
        float gaming_hours "Daily gaming hours"
        float stress_level "Academic stress (0 - 100)"
        float burnout_score "Burnout index (0 - 100)"
        float study_hours_daily "Study hours per day"
        float self_learning_hours "Self-learning hours per day"
        float gym_frequency "Days per week exercising"
        float wellness_score "Interaction wellness index"
        float screen_to_study_ratio "Screen-to-study ratio"
        string lifestyle_risk_flag "High Risk / Normal"
    }

    fact_career {
        string student_id PK, FK "References dim_student"
        float cgpa "Cumulative Grade Point Average (0 - 10)"
        int backlog_history "Number of active or past backlogs"
        int dsa_problems_solved "LeetCode / HackerRank problems"
        int internships_completed "Number of completed internships"
        int development_projects_count "Built projects count"
        int ai_ml_projects "AI / ML projects count"
        int git_hub_repos "Public repository count"
        float communication_skills "Communication rating (0 - 100)"
        float aptitude_score "Aptitude test rating (0 - 100)"
        float mock_interview_score "Mock interview rating (0 - 100)"
        float salary_lpa "Offered package (LPA)"
        string placement_status "Placed / Not Placed"
    }
```

---

## 4. Predictive Modeling & Anti-Leakage Architecture

### Target & Label Engineering
- **Model 1 (Academic Trajectory Regressor)**:
  - **Target**: `anchor_cgpa` (Continuous 0.0 – 10.0).
  - **Algorithm**: Gradient Boosting Regressor (28 features).
  - **Calibrated Baseline**: $R^2 = 0.2096$, $\text{RMSE} = 0.7581$, $\text{MAE} = 0.6022$.
  - **Operational Framing**: Captures directional movement from effort and study hours; disclosed as a low-confidence directional signal ($R^2 < 0.30$).
- **Model 2 (At-Risk Early Warning Classifier)**:
  - **Target**: `at_risk_flag` (Binary 0 or 1).
  - **Defining Formula**:
    $$\text{at\_risk\_flag} = 1 \iff (\text{backlogs} \ge 1 \lor \text{attendance} < 55\% \lor \text{CGPA} < 5.5)$$
  - **Class Distribution**: 31.89% At-Risk (7,973 students) vs 68.11% Safe (17,027 students).
  - **Algorithm**: Balanced Logistic Regression Classifier (23 lifestyle features).
  - **Calibrated Baseline**: Recall = 0.5022, Precision = 0.3346, ROC AUC = 0.5190, Accuracy = 0.5226 at 0.50 decision threshold.

### Strict Anti-Leakage Isolation Barrier

```mermaid
flowchart LR
    subgraph DefiningFormula["Target Definition (at_risk_flag)"]
        F1["anchor_backlog_history (>= 1)"]
        F2["anchor_attendance_percentage (< 55%)"]
        F3["anchor_cgpa (< 5.5)"]
    end

    subgraph LeakageWall["Strict Isolation Barrier"]
        BLOCKED["BLOCKED FROM MODEL 2 INPUTS\n- No Backlogs\n- No Attendance\n- No CGPA"]
    end

    subgraph Model2Features["Model 2 Safe Features (23 Lifestyle Attributes)"]
        L1["anchor_sleep_hours"]
        L2["anchor_screen_time"]
        L3["anchor_gaming_hours"]
        L4["anchor_stress_level"]
        L5["anchor_burnout_score"]
        L6["anchor_study_hours_daily"]
        L7["anchor_self_learning_hours"]
        L8["anchor_motivation_level"]
        L9["anchor_adaptability_score"]
        L10["anchor_gym_frequency"]
        L11["anchor_family_income_lpa"]
        L12["anchor_resume_score"]
        L13["anchor_communication_skills"]
        L14["anchor_aptitude_score"]
        L15["anchor_mock_interview_score"]
        L16["wellness_score"]
        L17["screen_to_study_ratio"]
        L18["projects & hackathons"]
    end

    subgraph Model2Output["Model 2 Inference"]
        M2["Balanced Random Forest Classifier\nThreshold = 0.50"]
        PRED["predicted_risk_probability\nis_predicted_at_risk"]
    end

    DefiningFormula -.-> BLOCKED
    BLOCKED -.-x Model2Features
    Model2Features --> M2
    M2 --> PRED
```

---

## 5. Branch-Adaptive Career Readiness Engine

The Career Readiness engine evaluates students on a 0 – 100 composite scale and performs peer comparisons against cohorts in the same branch and college tier. To prevent unfair bias, weighting dynamically adapts based on whether the student belongs to a Computer Science/Tech track or a Core Engineering track.

```mermaid
flowchart TD
    IN["Student Career Attributes\n(DSA, Internships, Projects, Aptitude, Comms, Mock)"] --> BR{"Branch Detection\nis_cs_branch(branch)?"}

    subgraph CSTrack["Computer Science Track (CSE, IT, AI & DS)"]
        W_CS["Adaptive Weights:\n- DSA Problem Solving: 25%\n- Internships: 20%\n- Technical Projects: 15%\n- Aptitude: 15%\n- Communication: 15%\n- Mock Interviews: 10%"]
    end

    subgraph NonCSTrack["Core Engineering Track (Mech, Civil, Chem, Elec)"]
        W_NCS["Adaptive Weights:\n- Technical Projects: 30%\n- Internships: 25%\n- Aptitude: 20%\n- Communication: 15%\n- Mock Interviews: 10%\n(DSA EXCLUDED - 0% Penalty)"]
    end

    BR -- Yes (CS Track) --> W_CS
    BR -- No (Non-CS Track) --> W_NCS

    W_CS --> COMP["Component Normalization (0 - 100)"]
    W_NCS --> COMP

    COMP --> SCORE["Composite Career Readiness Score (0 - 100)"]
    SCORE --> BENCH["Peer Benchmark Against Branch & Tier Cohort\n(student_master_wide.csv population)"]
    BENCH --> GAPS["Skill Gap Percentile Ranking & Action Plan"]
```

---

## 6. Stateless "Bring Your Own Data" (BYOD) Ingestion Flows

The `/api/assess/*` endpoints allow faculty, recruiters, and students to evaluate external student profiles without inserting, updating, or mutating a single row in the production data warehouse.

```mermaid
flowchart TD
    subgraph BYODOption1["Option 1: CSV Match & Confirm"]
        O1A["Upload CSV with arbitrary headers"] --> O1B["Fuzzy Header Matcher (Levenshtein & Synonyms)"]
        O1B --> O1C["Generate Preview & Return preview_id"]
        O1C --> O1D["User Confirms / Overrides Mapping"]
        O1D --> O1E["Batch Assessment Execution"]
    end

    subgraph BYODOption2["Option 2: Multi-CSV Stitching"]
        O2A["Upload 2-4 Split CSV Files"] --> O2B["Detect Shared Key or Demographic Attributes"]
        O2B --> O2C["Stitch Datasets with Lineage Disclosure"]
        O2C --> O2D["Batch Assessment Execution"]
    end

    subgraph BYODOption3["Option 3: Chatbot-Guided Assessment"]
        O3A["POST /api/assess/chat-guided"] --> O3B["Ask Branch & College Tier First"]
        O3B --> O3C{"Branch == CS?"}
        O3C -- Yes --> O3D["Include DSA Questions"]
        O3C -- No --> O3E["Skip DSA Questions -> Go to Internships"]
        O3D --> O3F["Accept Answers / 'skip' for Population Median"]
        O3E --> O3F
        O3F --> O3G["Session Complete -> Auto-Trigger Full Assessment"]
    end

    subgraph BYODOption4["Option 4: Direct Form Assessment"]
        O4A["POST /api/assess/new-student"] --> O4B["Direct JSON Input"]
    end

    subgraph CoreEngine["Shared Stateless Assessment Core (run_full_assessment)"]
        ENG1["Fill Missing Attributes with Warehouse Population Medians"]
        ENG2["Compute 5 Engineered Interaction Features"]
        ENG3["Model 1 Inference -> predicted_cgpa"]
        ENG4["Model 2 Inference -> at_risk_probability & label"]
        ENG5["Branch-Adaptive Career Readiness Calculation"]
        ENG6["Generate Plain-Language Narratives (Gemini / Fallback)"]
        ENG7["Compile Disclaimers & Audit Metadata"]
    end

    subgraph DBZeroMutation["Zero Database Mutation Guarantee"]
        NODB["READ-ONLY POPULATION ACCESS\nZero INSERT / UPDATE / DELETE statements executed"]
    end

    O1E --> CoreEngine
    O2D --> CoreEngine
    O3G --> CoreEngine
    O4B --> CoreEngine
    CoreEngine --> NODB
```

---

## 7. GenAI Copilot & Resilient Token Fallback Architecture

Campus360 integrates Google Gemini (`gemini-3.5-flash-lite`) for automated advisory generation. To ensure zero system crashes during live hackathon demonstrations or network outages, it implements an instant, deterministic statistical fallback pipeline.

```mermaid
flowchart TD
    CALL["GenAI Request\n(At-Risk Brief, Performance Trajectory, Career Plan, What-If)"] --> TOK{"is_gemini_token_available()?\n(GEMINI_API_KEY present?)"}
    
    TOK -- No (Token Missing) --> FB1["Activate Deterministic Rule Fallback\n- token_available: false\n- is_fallback: true\n- fallback_reason: 'Gemini API key is not configured'\n- fallback_notice: 'Gemini token is not available. Rule-grounded brief displayed.'"]
    
    TOK -- Yes (Token Present) --> CHK{"SHA-256 In-Memory Cache Hit?"}
    
    CHK -- Yes --> CACHE["Return Cached Narrative"]
    
    CHK -- No --> GEM["Execute Gemini API Call\n(gemini-3.5-flash-lite, timeout=7s, temp=0.2)"]
    
    GEM --> RESP{"API Response Status?"}
    
    RESP -- 200 OK --> SUC["Return AI Narrative\n- token_available: true\n- is_fallback: false"]
    
    RESP -- 429 Quota Exhausted --> FB2["Activate Deterministic Rule Fallback\n- token_available: true\n- is_fallback: true\n- fallback_reason: 'Gemini API quota exhausted (429)'"]
    
    RESP -- 503 Unavailable / Timeout --> FB3["Activate Deterministic Rule Fallback\n- token_available: true\n- is_fallback: true\n- fallback_reason: 'Gemini service unreachable (503/timeout)'"]

    FB1 --> LOG["Log Interaction & Return Structured JSON"]
    FB2 --> LOG
    FB3 --> LOG
    SUC --> LOG
    CACHE --> LOG
```

---

## 8. Runtime Service Topology & Docker Architecture

All platform services are containerized via Docker and Docker Compose.

```mermaid
graph TB
    subgraph Host["Host Machine (Local Development / Evaluation)"]
        Client["Browser Client (User / Evaluator)"]
    end

    subgraph DockerCompose["Docker Compose Network: campus360_default"]
        subgraph PostgresContainer["campus360_postgres (postgres:16)"]
            PG["PostgreSQL Database (port 5432)\n- Database: campus360_warehouse\n- Healthcheck: pg_isready\n- Volume: pgdata (persistent warehouse)"]
        end

        subgraph APIContainer["campus360_api (Python 3.11 FastAPI)"]
            UVI["Uvicorn Server (port 8000)"]
            FAST["FastAPI Engine"]
            MODELS["Scikit-Learn Model Artifacts\n- model1_performance_predictor.joblib\n- model2_atrisk_classifier.joblib"]
            GENAI["GenAI Engine (Gemini + Fallback)"]
            ASSESS["BYOD Assessment Engine"]
            FAST --> MODELS
            FAST --> GENAI
            FAST --> ASSESS
            UVI --> FAST
        end

        subgraph DashboardContainer["campus360_dashboard (Python HTTP Server)"]
            HTTP["Static Server (port 8501)\n- index.html (Analytics Dashboard)\n- assess.html (BYOD Studio)\n- arch.html (Architecture Explorer)\n- app.js, assess.js, styles.css"]
        end
    end

    Client -- "http://localhost:8501" --> HTTP
    Client -- "http://localhost:8000/api/*" --> UVI
    FAST -- "postgresql://campus360:...@postgres:5432/campus360_warehouse" --> PG
```

### Container Port & Volume Specifications

| Container Name | Base Image | Exposed Port | Purpose | Mounted Volumes |
|---|---|---|---|---|
| `campus360_postgres` | `postgres:16` | `5432:5432` | Star Schema Data Warehouse | `pgdata:/var/lib/postgresql/data` |
| `campus360_api` | `campus360-api` (Python 3.11-slim) | `8000:8000` | REST API, ML Inference, BYOD & GenAI | `./src:/app/src`, `./data:/app/data`, `./models:/app/models`, `./tests:/app/tests` |
| `campus360_dashboard` | `campus360-dashboard` (Python 3.11-slim) | `8501:8501` | Static Web Frontends | `./src/dashboard:/usr/share/campus360/dashboard` |

---

## 9. End-to-End Request & Data Lifecycle

To trace how a request flows through the entire system, consider a user submitting a direct assessment form for a **Mechanical Engineering student**:

1. **User Action**: The user selects `Mechanical` branch, enters attendance (82%), daily study hours (4.5), and internships (2) on `http://localhost:8501/assess.html`. The UI dynamically detects the non-CS branch and informs the user that DSA problem solving is omitted from scoring.
2. **HTTP Dispatch**: `assess.js` sends an HTTP POST request to `http://localhost:8000/api/assess/new-student`.
3. **Imputation**: `run_full_assessment()` intercepts the payload. Missing attributes (sleep hours, stress level, aptitude) are imputed with population medians from `student_master_wide.csv`.
4. **Feature Engineering**: Calculates `effort_score`, `screen_to_study_ratio`, and `wellness_score`. Non-CS students compute effort without DSA penalties.
5. **Model 1 Prediction**: The 28-feature vector is passed to `models/model1_performance_predictor.joblib`, predicting a CGPA of `7.32`.
6. **Model 2 Prediction**: The 23 lifestyle features (strictly excluding CGPA, backlogs, and attendance) are passed to `models/model2_atrisk_classifier.joblib`, returning an at-risk probability of `0.58` (`At-Risk`).
7. **Career Scoring**: `_compute_career_readiness()` detects `is_cs_branch("Mechanical") == False`, applies non-CS weights (Projects 30%, Internships 25%, Aptitude 20%, Communication 15%, Mock Interview 10%), benchmarks the student against Mechanical peers in Tier 2, and returns a Career Readiness Score of `49.3/100`.
8. **GenAI Narrative**: `generate_atrisk_brief()` calls Gemini. If `GEMINI_API_KEY` is not present or quota is exhausted (429), it returns the deterministic rule-grounded brief with `token_available` and `fallback_notice` metadata.
9. **Zero DB Mutation Verification**: No records are inserted into `dim_student`, `fact_performance`, `fact_lifestyle`, or `fact_career`.
10. **Response Rendering**: The frontend renders the predicted CGPA, risk badge, career breakdown, peer comparison, and AI mentor brief with crisp SVG icons and zero emojis.
