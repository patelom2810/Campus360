<div align="center">

# ![Campus360](src/dashboard/assets/logo-full.svg)

### Student Academic Success, Subject Performance & Career Readiness Analytics Platform
**KDAC-3 — KENEXA AI Hackathon**

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
├── data/       # Raw CSV datasets (70k rows), cleaned interim data, and stitched star-schema tables
├── src/        # Application source code (ETL pipelines, ML training, GenAI, FastAPI backend, Dashboard)
├── models/     # Serialized Scikit-Learn model artifacts (.joblib) for performance and risk prediction
├── docs/       # Comprehensive technical documentation, architecture specs, audits, and deployment guides
├── tests/      # Automated unit and integration test suites validating warehouse and API integrity
└── docker/     # Dockerfiles and entrypoint initialization scripts for containerized deployment
```

For the comprehensive file tree and component breakdown, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture, 6-dataset stitching methodology, 180k-row star schema, and data lineage.
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Multi-container Docker deployment guide, PostgreSQL migration, and SQLite fallback mechanism.
- [docs/DOCKER_VERIFICATION.md](docs/DOCKER_VERIFICATION.md) — Independent verification log of clean-state Docker execution, auto-ETL timing, and failure-recovery tests.
- [docs/FINAL_SUBMISSION_AUDIT.md](docs/FINAL_SUBMISSION_AUDIT.md) — Source of truth audit report verifying live row counts, model evaluations, leakage checks, and submission rubric coverage.

---

## Team

- **Team ID:** 60
- **Members:** Om Patel & Rahil Nagariya
- **Hackathon:** KDAC-3 — KENEXA AI Hackathon

<br>

<div align="center">

<img src="src/dashboard/assets/logo-icon.svg" alt="Campus360 Logo Mark" width="48" height="48" />

</div>
