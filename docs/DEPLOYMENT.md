# Campus360: Deployment & PostgreSQL Migration Master Guide

**Project:** Campus360 | **Problem Code:** KDAC-3 (KENEXA AI Hackathon)  
**Authors:** Om Patel & Rahil Nagariya (Team ID: 60)  
**Status:** Completed & Validated

---

## 1. PostgreSQL Warehouse Migration & Engineering Overview

The data warehouse layer of Campus360 was migrated from an embedded SQLite database to **PostgreSQL 16**, keeping the existing Star Schema, data stitching logic, and machine learning pipelines intact. In addition, an automatic, zero-downtime **SQLite local fallback** was built to guarantee presentation and demo safety on any laptop without Docker.

### Key Architectural Objectives
1. **Concurrency & High-Throughput Access:** Enable simultaneous, low-latency client-server connections from both the FastAPI backend (`src/api/main.py`) and the Streamlit analytical dashboard (`src/dashboard/app.py`).
2. **Strict Foreign Key Enforcement:** Enforce relational integrity across star schema tables (`fact_performance`, `fact_lifestyle`, and `fact_career` strictly reference `dim_student(student_id)`).
3. **Explicit Typing & DDL Mapping:** Eliminate silent type misinference for primary keys, academic marks, percentages, and financial packages.
4. **Production Containerization:** Integrate seamlessly into Docker multi-container orchestration via `postgres:16` with automated healthcheck polling.

---

## 2. Unchanged Upstream Layers (Zero Disruption)

- **Star Schema Design:** Preserves 1 dimension (`dim_student`) and 3 fact tables (`fact_performance`, `fact_lifestyle`, `fact_career`) without modifying table schemas or column names.
- **Data Stitching & Cleaning:** All raw-to-interim cleaning (`src/etl/clean.py`), attribute-based matching (`src/etl/stitch.py`), and master wide table generation remain untouched.
- **ML Training Pipelines:** Model 1 (Performance Regression), Model 2 (At-Risk Classifier), and Model 3 (Career Readiness) continue consuming their designated feature matrices from `data/processed/` with zero breaking changes.

---

## 3. Container Orchestration & Docker Architecture

### Root Docker Compose Configuration (`docker-compose.yml`)
```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    container_name: campus360_postgres
    environment:
      POSTGRES_USER: campus360
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: campus360_warehouse
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U campus360"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    container_name: campus360_api
    environment:
      - DB_ENGINE=postgres
      - DATABASE_URL=postgresql://campus360:${POSTGRES_PASSWORD:-changeme}@postgres:5432/campus360_warehouse
      - API_HOST=0.0.0.0
      - API_PORT=8000
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  dashboard:
    build:
      context: .
      dockerfile: docker/Dockerfile.dashboard
    container_name: campus360_dashboard
    environment:
      - DB_ENGINE=postgres
      - DATABASE_URL=postgresql://campus360:${POSTGRES_PASSWORD:-changeme}@postgres:5432/campus360_warehouse
      - STREAMLIT_PORT=8501
    ports:
      - "8501:8501"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

### Dockerfiles
- **`docker/Dockerfile.api`:** Python 3.11 slim image with `build-essential`, `libpq-dev`, `curl`, automated dependency caching, and Uvicorn server entrypoint on port `8000`.
- **`docker/Dockerfile.dashboard`:** Python 3.11 slim image with PostgreSQL client libraries and Streamlit server entrypoint on port `8501`.

---

## 4. Environment & Database Configuration

### Template: `.env.example`
```ini
# Database Engine Selection (postgres | sqlite)
DB_ENGINE=postgres

# PostgreSQL Configuration
POSTGRES_USER=campus360
POSTGRES_PASSWORD=changeme
POSTGRES_DB=campus360_warehouse
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://campus360:changeme@postgres:5432/campus360_warehouse

# Local Development / Non-Docker Database URL (uncomment when running outside Docker):
# DATABASE_URL=postgresql://campus360:changeme@localhost:5432/campus360_warehouse

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Streamlit Dashboard Configuration
STREAMLIT_PORT=8501

# LLM / GenAI API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 5. Star Schema PostgreSQL Loader (`src/etl/load.py`)

- **Engine:** SQLAlchemy 2.0 with `psycopg2-binary` driver.
- **Explicit Column DDL Mappings:**
  - `student_id`: `VARCHAR(16)` with `PRIMARY KEY` on `dim_student`.
  - Academic marks, exam weights, and percentages: `FLOAT`.
  - Financial salaries and family income: `FLOAT` / `NUMERIC`.
  - Demographic tiers, age, and backlogs: `INTEGER`.
- **Foreign Key Constraints:**
  ```sql
  ALTER TABLE fact_performance
  ADD CONSTRAINT fk_fact_perf_student
  FOREIGN KEY (student_id) REFERENCES dim_student(student_id) ON DELETE CASCADE;

  ALTER TABLE fact_lifestyle
  ADD CONSTRAINT fk_fact_life_student
  FOREIGN KEY (student_id) REFERENCES dim_student(student_id) ON DELETE CASCADE;

  ALTER TABLE fact_career
  ADD CONSTRAINT fk_fact_career_student
  FOREIGN KEY (student_id) REFERENCES dim_student(student_id) ON DELETE CASCADE;
  ```

---

## 6. Local SQLite Fallback Mechanism (Demo Safety)

To ensure fail-safe operation during live evaluations, pitch presentations, or environments where Docker/PostgreSQL is unavailable, a dynamic fallback mechanism is implemented:

- **Environment Variable:** `DB_ENGINE` (`postgres` | `sqlite`, default `postgres`).
- **Automatic Connection Fallback:** If `DB_ENGINE=postgres` but the PostgreSQL server is unreachable, `create_warehouse_engine()` automatically falls back to `data/processed/warehouse.db` and logs an alert.
- **Full Parity:** Both the FastAPI backend and Streamlit dashboard execute identical queries across both engines with zero API contract divergence.
- **Synchronized ETL:** `src/etl/load.py` updates both PostgreSQL and SQLite files on every ETL run, guaranteeing the offline backup is always up to date.

---

## 7. Verification & Validation Metrics

### Row Count Parity Verification
| Table | CSV Source Rows | PostgreSQL Rows | SQLite Rows | Relational Constraint |
|---|---|---|---|---|
| `dim_student` | 25,000 | 25,000 | 25,000 | Primary Key (`student_id`) |
| `fact_performance` | 105,000 | 105,000 | 105,000 | Foreign Key -> `dim_student(student_id)` |
| `fact_lifestyle` | 25,000 | 25,000 | 25,000 | Foreign Key -> `dim_student(student_id)` |
| `fact_career` | 25,000 | 25,000 | 25,000 | Foreign Key -> `dim_student(student_id)` |

### Automated Integration Test Suite (`tests/test_postgres_migration.py`)
- Tested table count matching against source CSVs (100% exact match).
- Verified foreign key enforcement by attempting orphan row insertion into `fact_career` (verified `IntegrityError` triggered).
- Verified API endpoint results match under both PostgreSQL and SQLite engines.
- Verified Docker Compose configuration syntax.
