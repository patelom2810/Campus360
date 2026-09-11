"""
FastAPI Backend for Campus360 Data Warehouse
Provides REST endpoints for querying student demographics, academic performance,
lifestyle metrics, and career readiness facts.

Supports dual-database engines:
  - PostgreSQL (Production / Docker): postgresql://campus360:...
  - SQLite (Local fallback): data/processed/warehouse.db
Configurable via DB_ENGINE environment variable (postgres | sqlite).
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.etl.load import create_warehouse_engine

app = FastAPI(
    title="Campus360 Analytics API",
    description="REST API for Campus360 Multi-Dimensional Student Warehouse",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    engine, engine_type = create_warehouse_engine()
    return {
        "project": "Campus360 Analytics Platform",
        "status": "online",
        "active_database_engine": engine_type,
        "docs_url": "/docs",
        "endpoints": [
            "/health",
            "/api/students",
            "/api/students/{student_id}",
            "/api/analytics/overview",
            "/api/analytics/departments",
            "/api/analytics/lifestyle",
        ]
    }


@app.get("/health")
def healthcheck():
    """Health check endpoint confirming database connectivity and table counts."""
    engine, engine_type = create_warehouse_engine()
    try:
        with engine.connect() as conn:
            counts = {}
            for table in ["dim_student", "fact_performance", "fact_lifestyle", "fact_career"]:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                counts[table] = cnt
            return {
                "status": "healthy",
                "database_engine": engine_type,
                "table_counts": counts,
            }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Database connectivity failed: {err}")


@app.get("/api/students")
def list_students(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    stream_branch: Optional[str] = None,
    college_tier: Optional[int] = None,
    state: Optional[str] = None,
):
    """Lists students from dim_student with optional branch, tier, and state filtering."""
    engine, engine_type = create_warehouse_engine()
    query = "SELECT * FROM dim_student WHERE 1=1"
    params = {"limit": limit, "offset": offset}

    if stream_branch:
        query += " AND stream_branch = :stream_branch"
        params["stream_branch"] = stream_branch
    if college_tier:
        query += " AND college_tier = :college_tier"
        params["college_tier"] = college_tier
    if state:
        query += " AND state = :state"
        params["state"] = state

    query += " ORDER BY student_id ASC LIMIT :limit OFFSET :offset"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        students = [dict(row._mapping) for row in result]

        total_query = "SELECT COUNT(*) FROM dim_student"
        total = conn.execute(text(total_query)).scalar()

    return {
        "engine": engine_type,
        "total_students": total,
        "returned": len(students),
        "limit": limit,
        "offset": offset,
        "students": students,
    }


@app.get("/api/students/{student_id}")
def get_student_360(student_id: str):
    """Returns comprehensive 360-degree profile for a single student."""
    engine, engine_type = create_warehouse_engine()
    sid = student_id.upper()

    with engine.connect() as conn:
        # Demographics
        dim = conn.execute(
            text("SELECT * FROM dim_student WHERE student_id = :sid"),
            {"sid": sid}
        ).fetchone()
        if not dim:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        # Performance facts
        perf = conn.execute(
            text("SELECT * FROM fact_performance WHERE student_id = :sid ORDER BY source, subject"),
            {"sid": sid}
        ).fetchall()

        # Lifestyle facts
        life = conn.execute(
            text("SELECT * FROM fact_lifestyle WHERE student_id = :sid"),
            {"sid": sid}
        ).fetchone()

        # Career facts
        career = conn.execute(
            text("SELECT * FROM fact_career WHERE student_id = :sid"),
            {"sid": sid}
        ).fetchone()

    return {
        "engine": engine_type,
        "student_id": sid,
        "demographics": dict(dim._mapping),
        "academics": [dict(r._mapping) for r in perf],
        "lifestyle": dict(life._mapping) if life else None,
        "career": dict(career._mapping) if career else None,
    }


@app.get("/api/analytics/overview")
def get_analytics_overview():
    """Returns warehouse-level KPI summaries."""
    engine, engine_type = create_warehouse_engine()

    with engine.connect() as conn:
        total_students = conn.execute(text("SELECT COUNT(*) FROM dim_student")).scalar()
        avg_cgpa = conn.execute(text("SELECT ROUND(AVG(cgpa)::numeric, 2) FROM fact_career")).scalar() if engine_type == "postgres" else conn.execute(text("SELECT ROUND(AVG(cgpa), 2) FROM fact_career")).scalar()
        high_risk_count = conn.execute(text("SELECT COUNT(*) FROM fact_lifestyle WHERE lifestyle_risk_flag = 'High Risk'")).scalar()
        placed_count = conn.execute(text("SELECT COUNT(*) FROM fact_career WHERE placement_status = 'Placed'")).scalar()
        avg_salary = conn.execute(text("SELECT ROUND(AVG(salary_lpa)::numeric, 2) FROM fact_career WHERE salary_lpa > 0")).scalar() if engine_type == "postgres" else conn.execute(text("SELECT ROUND(AVG(salary_lpa), 2) FROM fact_career WHERE salary_lpa > 0")).scalar()

    return {
        "engine": engine_type,
        "total_students": total_students,
        "average_cgpa": float(avg_cgpa) if avg_cgpa else None,
        "placement_rate_pct": round((placed_count / total_students) * 100, 2) if total_students else 0,
        "high_risk_lifestyle_pct": round((high_risk_count / total_students) * 100, 2) if total_students else 0,
        "average_salary_lpa": float(avg_salary) if avg_salary else None,
    }


@app.get("/api/analytics/departments")
def get_department_breakdown():
    """Returns analytics aggregated by engineering branch."""
    engine, engine_type = create_warehouse_engine()
    sql = """
        SELECT
            d.stream_branch,
            COUNT(d.student_id) AS student_count,
            ROUND(AVG(c.cgpa)::numeric, 2) AS avg_cgpa,
            ROUND(AVG(c.salary_lpa)::numeric, 2) AS avg_salary_lpa,
            SUM(CASE WHEN c.placement_status = 'Placed' THEN 1 ELSE 0 END) AS placed_count
        FROM dim_student d
        JOIN fact_career c ON d.student_id = c.student_id
        GROUP BY d.stream_branch
        ORDER BY student_count DESC
    """ if engine_type == "postgres" else """
        SELECT
            d.stream_branch,
            COUNT(d.student_id) AS student_count,
            ROUND(AVG(c.cgpa), 2) AS avg_cgpa,
            ROUND(AVG(c.salary_lpa), 2) AS avg_salary_lpa,
            SUM(CASE WHEN c.placement_status = 'Placed' THEN 1 ELSE 0 END) AS placed_count
        FROM dim_student d
        JOIN fact_career c ON d.student_id = c.student_id
        GROUP BY d.stream_branch
        ORDER BY student_count DESC
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
        departments = [dict(r._mapping) for r in rows]

    return {
        "engine": engine_type,
        "departments": departments
    }
