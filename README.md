# Student Academic Success, Subject Performance & Career Readiness Analytics Platform

An enterprise-grade, end-to-end student success analytics and career readiness intelligence platform. Integrates academic assessments, behavioural habits, and career placement metrics into a unified 360° student data warehouse and star schema.

---

## 🏗️ Project Architecture

```
Campus360/
│
├── venv/                              # Python virtual environment
│
├── data/
│   ├── raw/                           # 6 canonical raw datasets (unmodified)
│   │   ├── suvidya_student_performance.csv
│   │   ├── kundan_student_performance.csv
│   │   ├── sehaj_student_lifestyle.csv
│   │   ├── navinpatidar_indian_placement.csv
│   │   ├── sakharebharat_indian_placement_2025.csv
│   │   └── shambhuraje_placement_career_2026.csv
│   ├── interim/                       # Cleaned individual datasets (snake_case, imputed, clipped)
│   └── processed/                     # Final stitched warehouse tables (Star Schema & master wide)
│       ├── student_master_wide.csv    # Master wide table (25k rows, 112 cols, 0 PII)
│       ├── dim_student.csv            # Demographics dimension
│       ├── fact_performance.csv       # Normalized marks & exams fact table
│       ├── fact_lifestyle.csv         # Wellness, sleep & stress fact table
│       ├── fact_career.csv            # Skills, packages & placement fact table
│       ├── model1_performance_train.csv
│       ├── model1_performance_test.csv
│       ├── model2_atrisk_train.csv
│       ├── model2_atrisk_test.csv
│       └── warehouse.db               # Embedded SQLite database fallback
│
├── docs/                              # Consolidated Technical Documentation
│   ├── ARCHITECTURE.md                # Data engineering, stitching, lineage & label engineering
│   └── DEPLOYMENT.md                  # Container deployment, PostgreSQL migration & fallback
│
├── src/
│   ├── etl/
│   │   ├── extract.py                 # Raw dataset ingestion and profiling
│   │   ├── clean.py                   # Per-dataset cleaning, imputation & clipping
│   │   ├── stitch.py                  # Attribute-based matching & wide table merge
│   │   ├── load.py                    # Star schema PostgreSQL loader & SQLite fallback
│   │   ├── fix_and_prepare.py         # PII drop, casing standardization, at_risk_flag & splits
│   │   └── run_pipeline.py            # End-to-end pipeline runner
│   │
│   ├── models/
│   │   ├── train_performance_model.py # Regression: next-term marks prediction
│   │   ├── train_atrisk_model.py      # Classification: student at-risk detection
│   │   └── train_career_model.py      # Career fit & placement predictor
│   │
│   ├── genai/
│   │   └── insights.py                # GenAI faculty copilot & student intervention summaries
│   │
│   ├── dashboard/
│   │   ├── index.html                 # Modern HTML5 + Tailwind CSS + Vanilla JS dashboard
│   │   ├── app.js                     # Vanilla JS state, Chart.js lifecycle & fetch API
│   │   └── style.css                  # Custom tokens, Sora & Inter fonts, slider styles
│   │
│   └── api/
│       └── main.py                    # FastAPI service backend & model inference
│
├── notebooks/
│   └── eda.ipynb                      # Exploratory Data Analysis
│
├── docker/
│   ├── Dockerfile.api                 # API Docker container
│   └── Dockerfile.dashboard           # Lightweight static dashboard container (port 8501)
│
├── docker-compose.yml                 # Multi-container orchestration (PostgreSQL, API, Dashboard)
├── tests/                             # Automated unit and integration test suite
├── requirements.txt                   # Frozen dependencies
├── .env.example                       # Environment configuration template
├── .gitignore                         # Git ignore rules
└── README.md
```

---

## 📚 Documentation

For in-depth technical reports, data lineage, mathematical methodology, and deployment guides:
- 🏛️ **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md):** Complete technical report covering raw data extraction, attribute-based similarity stitching, data lineage, synthetic field audit, label engineering (`at_risk_flag`), and PII removal audit.
- 🚀 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md):** Production deployment guide detailing PostgreSQL 16 containerization, Docker Compose architecture, foreign key constraints, API endpoints, and the zero-downtime SQLite local fallback.

## ⚠️ Disclosed Limitations

> **Data-Stitching Methodology Caveat**: Our data-stitching methodology, while statistically validated for internal consistency, can introduce correlations between the join key (CGPA) and other academic fields that don't reflect genuine real-world relationships — a disclosed limitation of synthetic multi-source stitching, and a primary motivation for validating this platform against a real institution's naturally-linked data in future work.

---

## ⚡ Quick Start

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run ETL & Data Stitching Pipeline
Run the entire extraction, cleaning, attribute-based stitching, and star-schema warehouse generation with a single command:
```bash
python3 -m src.etl.run_pipeline
```
Or run quality fixes and model preparation:
```bash
python3 src/etl/fix_and_prepare.py
```

### 3. Launch Services
- **Run FastAPI Backend (serves API & static dashboard at /dashboard):**
  ```bash
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Run Standalone Static Dashboard (port 8501):**
  ```bash
  python3 -m http.server 8501 --directory src/dashboard
  ```
- **Or run everything via Docker Compose:**
  ```bash
  docker compose up --build
  ```

### 4. Run Test Suite
```bash
python3 -m unittest discover tests
```
