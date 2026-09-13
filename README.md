<div align="center">

<table>
  <tr>
    <td align="center" valign="middle" style="border: none; padding: 12px 18px;">
      <img src="src/dashboard/assets/campus360-logo.png" alt="Campus 360 Logo" width="135" />
    </td>
    <td align="left" valign="middle" style="border: none; padding: 12px 18px;">
      <h1 style="margin: 0; padding: 0; border-bottom: none;">Campus 360 | By Neural Networks</h1>
      <h3 style="margin: 6px 0 8px 0; padding: 0; border-bottom: none; color: #6c5ce7;">Team ID: 60 &bull; KDAC-3 &bull; Kenexai</h3>
      <p style="margin: 0 0 6px 0; font-size: 15px;"><strong>Student Academic Success, Subject Performance &amp; Career Readiness Analytics Platform</strong></p>
      <p style="margin: 0; font-size: 13.5px; color: #666;"><strong>Authors:</strong> OM PATEL [Leader] &bull; Rahil Nagariya [Member]</p>
    </td>
  </tr>
</table>

  <p>
    <a href="#what-it-does">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#documentation">Documentation</a> •
    <a href="#team--authors">Team & Authors</a>
  </p>

</div>

Higher education institutions routinely isolate student data across disconnected ERP systems, academic mark sheets, wellness surveys, and placement portals, leaving advisors without an integrated view of student progress. Campus360 solves this by ingesting and stitching 6 independent Indian student datasets (70,000 raw records) into a unified 25,000-student PostgreSQL star-schema warehouse, analyzing multi-branch academic performance, detecting early at-risk indicators, predicting performance trends, and benchmarking career readiness against peer cohorts. Its standout differentiator is a Google Gemini GenAI intelligence layer that translates predictive model outputs into actionable, faculty-readable intervention briefs and student mentoring narratives—with every statistical claim and model limitation honestly calibrated rather than oversold.

---

## What It Does

- **Academic Performance:** Standardizes heterogeneous exam marks and degree CGPA onto a unified scale to track student progress across semesters and degree branches.
- **Learning Gaps:** Identifies branch-level subject weaknesses through interactive gap severity heatmaps so departments can target curriculum interventions.
- **At-Risk Detection:** Screens students early using lifestyle and behavioral telemetry to surface individuals who may need counseling before exams or backlogs occur.
- **Trend Prediction:** Projects future CGPA trajectories via an interactive simulator, helping students and advisors evaluate the impact of study habits and attendance.
- **Career Guidance:** Benchmarks technical and soft skills against branch peers to recommend personalized focus areas and reference historical placement outcomes.

---

## Architecture

```
6 Raw Datasets (70k rows) -> Attribute-Based Stitching -> PostgreSQL Star Schema (180k rows) -> ML Models (Performance Regressor + At-Risk Classifier) -> GenAI Layer (Google Gemini) -> Analytics Dashboard (7 views) -> Dockerized Deployment
```

For complete technical specifications, schema definitions, and data lineage, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).  
For the complete end-to-end system architecture and interactive data flow diagrams (ETL, Star Schema, ML Anti-Leakage, Branch-Adaptive Career Engine, BYOD Ingestion, and Docker topology), see [docs/SYSTEM_ARCHITECTURE_FLOW.md](docs/SYSTEM_ARCHITECTURE_FLOW.md).

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Data Engineering** | Python 3.11, Pandas, PostgreSQL 16 (Star Schema), SQLite fallback, Docker Compose |
| **Machine Learning** | Scikit-Learn (GradientBoostingRegressor, RandomForestClassifier), Joblib |
| **Generative AI** | Google Gemini API (with deterministic offline fallback engine) |
| **Backend API** | FastAPI, Uvicorn, SQLAlchemy, Pydantic |
| **Frontend Dashboard** | HTML5, Tailwind CSS, Vanilla JavaScript, Chart.js |

---

## Quick Start

```bash
docker compose up --build
```

Once running, access the platform services:
- **Dashboard:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (or standalone on port 8501: [http://localhost:8501](http://localhost:8501))
- **REST API:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

> **First Run Timing:** `docker compose up --build` takes ~5.3 minutes total from scratch without layer cache (~5.1 minutes for image build and dependency installation, and **11.92 seconds** for container startup and the automated ETL entrypoint to populate all 180,000 rows into PostgreSQL). Subsequent runs with pre-built images start in **~12–16 seconds** (or **~3–5 seconds** on existing volumes). For the full audit, see [docs/DOCKER_VERIFICATION.md](docs/DOCKER_VERIFICATION.md).
> 
> **Port 5432 Conflict Note:** If your host machine already runs a local PostgreSQL service on port 5432, stop it before starting Docker (`brew services stop postgresql@16` or `sudo systemctl stop postgresql`), or toggle `DB_ENGINE=sqlite` to evaluate Campus360 using the built-in standalone database.

---

## Dashboard Views

1. **View 7: Data & ETL Monitoring (`data-view="pipeline"`) — Default Landing View:** Live vertical flow status of the entire 7-stage data pipeline, displaying operational integrity progress (100%), 30s auto-refresh polling ticker, raw file table, interim duplicate pruning metrics (-10k rows), star-schema row counts (180,000), and model limitation disclosures.
2. **View 1: Executive Overview (`data-view="overview"`):** Institutional KPI metric cards (25,000 students, 7.46 avg CGPA, 98.38% placement rate, 31.9% at-risk baseline), 5-bin CGPA histogram distribution, and prioritized at-risk student quicklist.
3. **View 2: Subject Performance & Gaps (`data-view="subjects"`):** Standardized 0–100% subject score averages, 6x6 branch-by-subject gap severity heatmap, and branch-wise lowest subject gap action cards.
4. **View 3: At-Risk Detection (`data-view="atrisk"`):** Prominent amber model calibration banner (45% recall / 32% precision), top 5 lifestyle driving factors, and interactive searchable, sortable at-risk roster with direct 360° profile jump links.
5. **View 4: Trajectory Predictor (`data-view="predict"`):** Interactive student trajectory simulator powered by Model 1 with real-time sliders for study hours, sleep, attendance, and DSA problem counts.
6. **View 5: Student 360° Profile (`data-view="student"`):** Multi-dimensional individual dossier detailing demographics, multi-semester academic trends, wellness metrics, matched secondary source chips, and modal trigger for AI Mentor Briefs.
7. **View 6: Career Guidance (`data-view="career"`):** Career readiness index (0–100), branch peer benchmark, 6-component skill gap percentiles, suggested focus area recommendations, peer placement references, and personalized AI narrative.

---

## Model Performance — Reported Honestly

| Model | Metric | Result | Assessment |
| :--- | :--- | :---: | :--- |
| **Performance Prediction (CGPA)** | R² | 0.2096 | Weak — directional signal only |
| **At-Risk Detection** | Recall / AUC | 45.14% / 0.5044 | Weak — screening tool, not a diagnostic trigger |

We report these honestly rather than hide them — see [docs/FINAL_SUBMISSION_AUDIT.md](docs/FINAL_SUBMISSION_AUDIT.md) for the full methodology, leakage checks, and why these numbers are what they are.

---

## Known Limitations

- **Model 1 Low Variance Explained ($R^2 = 0.2096$, $\text{RMSE} = 0.7581$):** Lifestyle and aptitude metrics explain ~21% of CGPA variance; the model offers directional guidance rather than deterministic grade forecasting.
- **Model 2 Early-Stage Screening Quality ($\text{Recall} = 45.14\%$, $\text{Precision} = 32.30\%$, $\text{AUC} = 0.5044$):** Academic defining features (CGPA, backlogs, attendance) were strictly excluded to avoid circular target leakage, leaving lifestyle signals with weak separation (~2 in 3 flags are false alarms).
- **Suvidya Ceiling Test Confound ($\Delta\text{AUC} = +0.2663$):** Adding academic features lifted AUC from 0.6065 to 0.8728 on `suvidya_pass_fail`, but the lift is confounded because `anchor_cgpa` was the similarity key used in data stitching.
- **GenAI External Latency & Fallbacks:** Google Gemini API calls can encounter upstream latency or `503` errors; in-memory caching and deterministic rule-based template fallbacks guarantee continuous operation.
- **Cross-Cohort Secondary Sparsity:** Secondary datasets cover between 1,000 and 15,000 students of the 25,000 anchor cohort, requiring ML models to rely strictly on complete anchor attributes.

---

## Project Structure

```
Campus360/
├── docker/                             # Docker configuration and container entrypoints
│   ├── Dockerfile.api                  # Python 3.11 FastAPI backend container specification
│   ├── Dockerfile.dashboard            # Lightweight HTTP static frontend dashboard container
│   └── entrypoint.sh                   # Auto-initialization entrypoint (database setup & ETL loader)
├── docker-compose.yml                  # Multi-service orchestration (Postgres, API, Dashboard)
├── docs/                               # Comprehensive technical documentation & audits
│   ├── SYSTEM_ARCHITECTURE_FLOW.md     # Interactive system architecture & 7 Mermaid data flows
│   ├── ARCHITECTURE.md                 # Data engineering, stitching methodology & star schema specs
│   ├── DEPLOYMENT.md                   # Multi-container Docker deployment & SQLite fallback guide
│   ├── DOCKER_VERIFICATION.md          # Clean-state verification audit & recovery test logs
│   ├── FINAL_SUBMISSION_AUDIT.md       # Ground-truth submission audit, metrics & rubric verification
│   └── TECHNICAL_DEEP_DIVE.md          # In-depth algorithmic, statistical & leakage analysis
├── data/                               # Data storage across raw, interim, and warehouse tiers
│   ├── raw/                            # 6 untouched original datasets (70k total raw rows)
│   │   ├── shambhuraje_placement_career_2026.csv   # Master anchor spine (25k rows)
│   │   ├── kundan_student_performance.csv          # Secondary academics (Math, Science, English)
│   │   ├── sakharebharat_indian_placement_2025.csv # Engineering placement & skill ratings
│   │   ├── suvidya_student_performance.csv         # Intermediate marks & pass/fail status
│   │   ├── sehaj_student_lifestyle.csv             # Lifestyle habits & daily wellness telemetry
│   │   └── navinpatidar_indian_placement.csv       # Campus recruiters & salary packages
│   ├── interim/                        # Cleaned, deduplicated & scale-standardized CSVs (0 nulls)
│   └── processed/                      # Production Star Schema warehouse & training data
│       ├── dim_student.csv             # Student demographic & institutional dimension (25,000 rows)
│       ├── fact_performance.csv        # Long-format subject performance fact table (105,000 rows)
│       ├── fact_lifestyle.csv          # Habits, sleep, stress & wellness fact table (25,000 rows)
│       ├── fact_career.csv             # Skills, backlogs, placement & salary fact table (25,000 rows)
│       ├── student_master_wide.csv     # Unified master wide cohort dataset (112 columns)
│       ├── warehouse.db                # Standalone SQLite database for local fallback
│       ├── model1_performance_train.csv / test.csv # Stratified 80/20 performance splits
│       └── model2_atrisk_train.csv / test.csv      # Stratified 80/20 at-risk splits
├── src/                                # Application source code
│   ├── etl/                            # Modular data engineering & stitching pipeline
│   │   ├── extract.py                  # Ingestion profiling & schema discovery
│   │   ├── clean.py                    # Deduplication, imputation & range clipping
│   │   ├── stitch.py                   # Attribute-based statistical similarity matching
│   │   ├── fix_and_prepare.py          # PII removal, at_risk_flag calibration & splits
│   │   ├── load.py                     # PostgreSQL star schema loader & SQLite fallback
│   │   └── run_pipeline.py             # CLI runner orchestrating Stages 1-4 end-to-end
│   ├── models/                         # Machine learning model training scripts
│   │   ├── train_performance_model.py  # Model 1: Gradient Boosting CGPA regressor
│   │   ├── train_atrisk_model.py       # Model 2: Balanced Random Forest at-risk classifier
│   │   ├── train_career_model.py       # Career readiness multi-pillar scoring engine
│   │   └── train_suvidya_ceiling_test.py # Non-circular ceiling validation harness
│   ├── api/                            # Production FastAPI backend services
│   │   ├── main.py                     # REST API endpoints, routing & error handlers
│   │   └── assessment_engine.py        # Stateless BYOD engine & branch-adaptive weighting
│   ├── genai/                          # Generative AI copilot layer
│   │   └── insights.py                 # Google Gemini API client with deterministic fallback
│   └── dashboard/                      # Web dashboard & presentation layer
│       ├── index.html                  # Main analytics dashboard UI (7 interactive views)
│       ├── app.js                      # Dynamic charts (Chart.js), sliders & view state logic
│       ├── assess.html                 # BYOD interactive assessment studio UI (4 intake flows)
│       ├── assess.js                   # Assessment client logic, fuzzy matcher & chat flow
│       ├── arch.html                   # Interactive 11-slide architecture presentation deck
│       ├── app.py                      # Multi-tab Streamlit warehouse explorer
│       ├── style.css                   # Custom theme tokens, cards, and transitions
│       └── assets/                     # Official brand logos, vector SVGs & visual emblems
├── models/                             # Serialized Scikit-Learn models & evaluation metrics
│   ├── model1_performance_predictor.joblib   # Trained Model 1 pipeline artifact
│   ├── model1_performance_metrics.json       # Model 1 evaluation metrics (R², RMSE, MAE)
│   ├── model2_atrisk_classifier.joblib       # Trained Model 2 pipeline artifact
│   └── model2_atrisk_metrics.json           # Model 2 evaluation metrics (Recall, Prec, AUC)
├── model_experiments/                  # Model comparison & benchmarking harness
│   ├── run_comparison.py               # Evaluates 6 regression & 12 classification models
│   └── results/comparison_report.md    # Formatted evaluation & production swap policy report
├── tests/                              # Automated unit, integration & quality test suites
│   ├── test_assess_api.py              # BYOD assessment endpoints & CS vs non-CS branch tests
│   ├── test_dashboard_api.py           # Analytics API endpoints & filter validation
│   ├── test_etl_pipeline.py            # Stitching, row counts, and null integrity tests
│   ├── test_fix_and_prepare.py         # PII removal audit & label balance tests
│   ├── test_model_quality.py           # Anti-leakage checks, metric parity & sanity audits
│   └── test_postgres_migration.py      # PostgreSQL connection, schema, and fallback tests
└── requirements.txt                    # Project Python dependencies
```

---

## Documentation

- [docs/SYSTEM_ARCHITECTURE_FLOW.md](docs/SYSTEM_ARCHITECTURE_FLOW.md) — Comprehensive end-to-end system architecture with 7 interactive Mermaid data flow diagrams.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture, 6-dataset stitching methodology, 180k-row star schema, and data lineage.
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Multi-container Docker deployment guide, PostgreSQL migration, and SQLite fallback mechanism.
- [docs/DOCKER_VERIFICATION.md](docs/DOCKER_VERIFICATION.md) — Independent verification log of clean-state Docker execution, auto-ETL timing, and failure-recovery tests.
- [docs/FINAL_SUBMISSION_AUDIT.md](docs/FINAL_SUBMISSION_AUDIT.md) — Source of truth audit report verifying live row counts, model evaluations, leakage checks, and submission rubric coverage.
- [docs/TECHNICAL_DEEP_DIVE.md](docs/TECHNICAL_DEEP_DIVE.md) — In-depth algorithmic, statistical, and leakage prevention analysis.

---

## Team & Authors — Neural Networks
<a id="team--authors"></a>

**Company:** Kenexai | **Project:** KDAC-3: Student Academic Success, Subject Performance & Career Readiness Analytics Platform  
**Team Name:** Neural Networks | **Team ID:** 60

| Contributor | Project Role |
| :--- | :--- |
| **OM PATEL** | Team Leader & Full-Stack Architect |
| **Rahil Nagariya** | Team Member & Data Engineer |

- **Team Name:** Neural Networks
- **Team ID:** 60
- **Company:** Kenexai
- **Hackathon:** KDAC-3 — KENEXA AI Hackathon
- **Team Members:**
  - OM PATEL [Leader]
  - Rahil Nagariya [Member]

<br />

<div align="center">

  <img src="src/dashboard/assets/campus360-logo.png" alt="Campus360 Official Logo Mark" width="80" />

  <p><em>Campus 360 | By Neural Networks (Team ID: 60) &bull; Built with precision by OM PATEL & Rahil Nagariya for student academic success and career intelligence.</em></p>

</div>
