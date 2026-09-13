# Campus360: End-to-End System Architecture & Data Flow

**Platform:** Campus360 • Student Academic Success, Risk & Career Intelligence  
**Problem Code:** KDAC-3 (KENEXA AI Hackathon) | **Company:** Kenexai  
**Team Name:** Neural Nexus | **Team ID:** 60  
**Team Members:** OM PATEL [Leader], Rahil Nagariya [Member]  
**Status:** Production-Ready & Containerized  
**Zero Emojis Policy:** Strict text tags and vector SVG visual standards enforced  

---

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
        M2["Model 2: Balanced Random Forest\n(Predicts at_risk_flag, Recall=0.4514, 23 features)"]
        LK["Strict Anti-Leakage Isolation Barrier\n(Excludes attendance, backlogs, cgpa from M2)"]
    end

    subgraph AnalyticsEngine["5. Domain Logic & Assessment Engines"]
        CR["Branch-Adaptive Career Engine\n(CS vs Non-CS Dynamic Weights)"]
        WI["Real-time What-If Simulator"]
        BYOD["BYOD Assessment Engine (Stateless)\n- Option 1: CSV Match & Confirm\n- Option 2: Multi-CSV Stitching\n- Option 3: Chatbot Guided\n- Option 4: Direct Form"]
    end

    subgraph GenAITier["6. Resilient GenAI Copilot (Gemini API)"]
        GA["Google Gemini Pipeline (gemini-2.5-flash)"]
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
  - **Algorithm**: Balanced Random Forest Classifier (23 lifestyle features).
  - **Calibrated Baseline**: Recall = 0.4514, Precision = 0.3230, Accuracy = 0.5232 at 0.50 decision threshold.

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

Campus360 integrates Google Gemini (`gemini-2.5-flash`) for automated advisory generation. To ensure zero system crashes during live hackathon demonstrations or network outages, it implements an instant, deterministic statistical fallback pipeline.

```mermaid
flowchart TD
    CALL["GenAI Request\n(At-Risk Brief, Performance Trajectory, Career Plan, What-If)"] --> TOK{"is_gemini_token_available()?\n(GEMINI_API_KEY present?)"}
    
    TOK -- No (Token Missing) --> FB1["Activate Deterministic Rule Fallback\n- token_available: false\n- is_fallback: true\n- fallback_reason: 'Gemini API key is not configured'\n- fallback_notice: 'Gemini token is not available. Rule-grounded brief displayed.'"]
    
    TOK -- Yes (Token Present) --> CHK{"SHA-256 In-Memory Cache Hit?"}
    
    CHK -- Yes --> CACHE["Return Cached Narrative"]
    
    CHK -- No --> GEM["Execute Gemini API Call\n(gemini-2.5-flash, timeout=12s, temp=0.2)"]
    
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
