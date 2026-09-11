"""
Campus360 Analytics Platform - Streamlit Dashboard
Interactive data warehouse visualization and Student 360 Explorer.

Supports:
  - Live PostgreSQL Warehouse (Production / Docker)
  - SQLite Warehouse Fallback (Local Offline / Demo)
Configurable via DB_ENGINE environment variable or sidebar selector.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.etl.load import create_warehouse_engine

st.set_page_config(
    page_title="Campus360 | Student Intelligence Warehouse",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# Database Connection & Query Caching
# -----------------------------------------------------------------------------
@st.cache_resource
def get_engine(engine_choice: str):
    """Returns SQLAlchemy engine for selected engine choice."""
    engine, active_type = create_warehouse_engine(engine_choice.lower())
    return engine, active_type


@st.cache_data(ttl=600)
def load_kpis(engine_choice: str):
    engine, _ = get_engine(engine_choice)
    with engine.connect() as conn:
        total_students = conn.execute(text("SELECT COUNT(*) FROM dim_student")).scalar()
        avg_cgpa = conn.execute(text("SELECT AVG(cgpa) FROM fact_career")).scalar()
        placed_count = conn.execute(text("SELECT COUNT(*) FROM fact_career WHERE placement_status = 'Placed'")).scalar()
        avg_salary = conn.execute(text("SELECT AVG(salary_lpa) FROM fact_career WHERE salary_lpa > 0")).scalar()
        high_risk_count = conn.execute(text("SELECT COUNT(*) FROM fact_lifestyle WHERE lifestyle_risk_flag = 'High Risk'")).scalar()

    return {
        "total_students": total_students or 0,
        "avg_cgpa": round(avg_cgpa, 2) if avg_cgpa else 0.0,
        "placement_rate": round((placed_count / total_students) * 100, 1) if total_students else 0.0,
        "avg_salary": round(avg_salary, 2) if avg_salary else 0.0,
        "high_risk_pct": round((high_risk_count / total_students) * 100, 1) if total_students else 0.0,
    }


@st.cache_data(ttl=600)
def load_branch_analytics(engine_choice: str):
    engine, _ = get_engine(engine_choice)
    query = """
        SELECT
            d.stream_branch,
            COUNT(d.student_id) AS student_count,
            AVG(c.cgpa) AS avg_cgpa,
            AVG(c.salary_lpa) AS avg_salary_lpa,
            SUM(CASE WHEN c.placement_status = 'Placed' THEN 1 ELSE 0 END) * 100.0 / COUNT(d.student_id) AS placement_pct
        FROM dim_student d
        JOIN fact_career c ON d.student_id = c.student_id
        GROUP BY d.stream_branch
        ORDER BY student_count DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df


@st.cache_data(ttl=600)
def load_performance_summary(engine_choice: str):
    engine, _ = get_engine(engine_choice)
    query = """
        SELECT
            source,
            subject,
            assessment_term,
            AVG(marks) AS avg_marks,
            AVG(attendance_pct) AS avg_attendance,
            COUNT(*) AS record_count
        FROM fact_performance
        GROUP BY source, subject, assessment_term
        ORDER BY source, subject
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df


@st.cache_data(ttl=600)
def load_lifestyle_sample(engine_choice: str, limit: int = 5000):
    engine, _ = get_engine(engine_choice)
    query = f"""
        SELECT
            sleep_hours,
            screen_time_hours,
            gaming_hours,
            stress_level,
            burnout_score,
            lifestyle_risk_flag
        FROM fact_lifestyle
        LIMIT {limit}
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df


@st.cache_data(ttl=600)
def load_career_sample(engine_choice: str, limit: int = 5000):
    engine, _ = get_engine(engine_choice)
    query = f"""
        SELECT
            company_type,
            work_mode,
            salary_lpa,
            cgpa,
            dsa_problems_solved,
            placement_status,
            backlogs
        FROM fact_career
        LIMIT {limit}
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df


def fetch_student_record(student_id: str, engine_choice: str):
    engine, _ = get_engine(engine_choice)
    sid = student_id.strip().upper()
    with engine.connect() as conn:
        dim = conn.execute(text("SELECT * FROM dim_student WHERE student_id = :sid"), {"sid": sid}).fetchone()
        if not dim:
            return None, None, None, None
        perf = conn.execute(text("SELECT * FROM fact_performance WHERE student_id = :sid"), {"sid": sid}).fetchall()
        life = conn.execute(text("SELECT * FROM fact_lifestyle WHERE student_id = :sid"), {"sid": sid}).fetchone()
        career = conn.execute(text("SELECT * FROM fact_career WHERE student_id = :sid"), {"sid": sid}).fetchone()

    return (
        dict(dim._mapping),
        [dict(r._mapping) for r in perf],
        dict(life._mapping) if life else {},
        dict(career._mapping) if career else {},
    )


# -----------------------------------------------------------------------------
# Sidebar Configuration & Engine Selector
# -----------------------------------------------------------------------------
st.sidebar.image("https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=600&auto=format&fit=crop&q=80", use_container_width=True)
st.sidebar.title("Campus360 Settings")
st.sidebar.markdown("**Institutional Student Intelligence Platform**")

default_engine = os.getenv("DB_ENGINE", "postgres").lower()
engine_options = ["Postgres", "SQLite"]
engine_idx = 0 if default_engine == "postgres" else 1

selected_engine = st.sidebar.radio(
    "Data Warehouse Engine",
    options=engine_options,
    index=engine_idx,
    help="Switch between PostgreSQL (production warehouse) and SQLite (local backup).",
)

# Test active engine
engine_obj, active_engine_type = get_engine(selected_engine)
if active_engine_type == "postgres":
    st.sidebar.success("🟢 Active: **PostgreSQL Warehouse**")
else:
    st.sidebar.warning("🟡 Active: **SQLite Local Fallback**")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Warehouse Architecture:**
    - `dim_student`: 25,000 students
    - `fact_performance`: 105,000 records
    - `fact_lifestyle`: 25,000 records
    - `fact_career`: 25,000 records
    """
)


# -----------------------------------------------------------------------------
# Main Header & High-Level KPIs
# -----------------------------------------------------------------------------
st.title("🎓 Campus360: Student Intelligence & Warehouse Platform")
st.markdown("Multi-source academic, lifestyle, and career readiness analytics powered by a unified Star Schema.")

kpis = load_kpis(selected_engine)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Total Students", f"{kpis['total_students']:,}")
with c2:
    st.metric("Average CGPA", f"{kpis['avg_cgpa']:.2f} / 10.0")
with c3:
    st.metric("Placement Rate", f"{kpis['placement_rate']:.1f}%")
with c4:
    st.metric("Avg Package", f"₹{kpis['avg_salary']:.1f} LPA")
with c5:
    st.metric("Lifestyle At-Risk", f"{kpis['high_risk_pct']:.1f}%", delta="-Early Warning", delta_color="inverse")

st.markdown("---")

# -----------------------------------------------------------------------------
# Dashboard Tabs
# -----------------------------------------------------------------------------
tab_exec, tab_academics, tab_wellness, tab_career, tab_explorer = st.tabs([
    "🏛 Executive Overview",
    "📈 Academic Performance",
    "🧘 Lifestyle & Mental Wellness",
    "💼 Placement & Career Readiness",
    "🔍 Student 360 Explorer",
])

# TAB 1: EXECUTIVE OVERVIEW
with tab_exec:
    st.subheader("Departmental Distribution & Placement Success")
    branch_df = load_branch_analytics(selected_engine)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_branch = px.bar(
            branch_df,
            x="stream_branch",
            y="student_count",
            color="avg_cgpa",
            title="Student Population & Average CGPA by Branch",
            labels={"stream_branch": "Branch", "student_count": "Students", "avg_cgpa": "Avg CGPA"},
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig_branch, use_container_width=True)

    with col_chart2:
        fig_sal = px.bar(
            branch_df,
            x="stream_branch",
            y="avg_salary_lpa",
            color="placement_pct",
            title="Average Salary (LPA) & Placement Rate (%) by Branch",
            labels={"stream_branch": "Branch", "avg_salary_lpa": "Avg Salary (LPA)", "placement_pct": "Placement %"},
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig_sal, use_container_width=True)

    st.dataframe(
        branch_df.style.format({
            "avg_cgpa": "{:.2f}",
            "avg_salary_lpa": "{:.2f} LPA",
            "placement_pct": "{:.1f}%",
        }),
        use_container_width=True
    )

# TAB 2: ACADEMIC PERFORMANCE
with tab_academics:
    st.subheader("Normalized Subject Marks & Term Assessments (`fact_performance`)")
    perf_df = load_performance_summary(selected_engine)

    fig_marks = px.bar(
        perf_df,
        x="subject",
        y="avg_marks",
        color="source",
        barmode="group",
        title="Average Marks by Subject & Source System",
        labels={"avg_marks": "Average Score", "subject": "Subject", "source": "Dataset Source"},
    )
    st.plotly_chart(fig_marks, use_container_width=True)

    st.markdown("#### Source-Wise Examination Breakdown")
    st.dataframe(
        perf_df.style.format({
            "avg_marks": "{:.2f}",
            "avg_attendance": "{:.1f}%",
            "record_count": "{:,}",
        }),
        use_container_width=True
    )

# TAB 3: LIFESTYLE & WELLNESS
with tab_wellness:
    st.subheader("Student Wellness, Stress & Sleep Correlation (`fact_lifestyle`)")
    life_df = load_lifestyle_sample(selected_engine)

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        fig_scatter = px.scatter(
            life_df.sample(min(1500, len(life_df))),
            x="sleep_hours",
            y="stress_level",
            color="lifestyle_risk_flag",
            title="Daily Sleep Duration vs Reported Stress Level",
            labels={"sleep_hours": "Sleep (Hours/Day)", "stress_level": "Stress Level (0-100)"},
            color_discrete_map={"High Risk": "#e74c3c", "Normal": "#2ecc71"},
            opacity=0.6,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_w2:
        fig_burnout = px.histogram(
            life_df,
            x="burnout_score",
            color="lifestyle_risk_flag",
            title="Burnout Score Distribution across Population",
            labels={"burnout_score": "Burnout Score (0-100)"},
            nbins=30,
            color_discrete_map={"High Risk": "#e74c3c", "Normal": "#2ecc71"},
        )
        st.plotly_chart(fig_burnout, use_container_width=True)

# TAB 4: CAREER & PLACEMENT READINESS
with tab_career:
    st.subheader("Corporate Recruiter Profiles & Coding Metrics (`fact_career`)")
    car_df = load_career_sample(selected_engine)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        comp_dist = car_df["company_type"].value_counts().reset_index()
        comp_dist.columns = ["company_type", "count"]
        fig_pie = px.pie(
            comp_dist,
            names="company_type",
            values="count",
            title="Hiring Company Types Distribution",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_c2:
        fig_dsa = px.scatter(
            car_df[car_df["salary_lpa"] > 0].sample(min(1500, len(car_df))),
            x="dsa_problems_solved",
            y="salary_lpa",
            color="company_type",
            title="LeetCode/DSA Problems Solved vs Offered Salary Package (LPA)",
            labels={"dsa_problems_solved": "DSA Problems Solved", "salary_lpa": "Package (LPA)"},
            opacity=0.7,
        )
        st.plotly_chart(fig_dsa, use_container_width=True)

# TAB 5: STUDENT 360 EXPLORER
with tab_explorer:
    st.subheader("Single Student 360-Degree Institutional Dossier")

    c_search1, c_search2 = st.columns([1, 3])
    with c_search1:
        target_student_id = st.text_input("Enter Student ID:", value="STU00001", max_chars=8)

    dim, perf, life, career = fetch_student_record(target_student_id, selected_engine)

    if not dim:
        st.error(f"Student record '{target_student_id}' not found in warehouse.")
    else:
        st.success(f"**Found Master Profile:** {target_student_id} — {dim.get('degree')} in {dim.get('stream_branch')}")

        st.markdown("### 1. Demographics & Institutional Metadata")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        col_d1.metric("Gender / Age", f"{dim.get('gender')} ({dim.get('age')} yrs)")
        col_d2.metric("College / City Tier", f"College T{dim.get('college_tier')} / City T{dim.get('city_tier')}")
        col_d3.metric("State", f"{dim.get('state')}")
        col_d4.metric("Family Income", f"₹{dim.get('family_income_lpa')} LPA")

        st.markdown("### 2. Academic Performance Records Across Sources")
        if perf:
            perf_table = pd.DataFrame(perf)[["source", "assessment_term", "subject", "marks", "max_marks", "attendance_pct", "grade_or_status"]]
            st.dataframe(perf_table, use_container_width=True)
        else:
            st.info("No detailed subject exam records found.")

        col_bot1, col_bot2 = st.columns(2)
        with col_bot1:
            st.markdown("### 3. Wellness & Habits (`fact_lifestyle`)")
            if life:
                st.write(f"- **Sleep Hours:** {life.get('sleep_hours')} hrs/day")
                st.write(f"- **Daily Screen Time:** {life.get('screen_time_hours')} hrs")
                st.write(f"- **Stress Level:** {life.get('stress_level')} / 100")
                st.write(f"- **Burnout Score:** {life.get('burnout_score')} / 100")
                st.write(f"- **Gym Frequency:** {life.get('gym_frequency_per_week')} days/week")
                risk = life.get('lifestyle_risk_flag')
                if risk == "High Risk":
                    st.error(f"⚠️ Flagged: **{risk}**")
                else:
                    st.success(f"✅ Status: **{risk}**")

        with col_bot2:
            st.markdown("### 4. Career Readiness & Placement (`fact_career`)")
            if career:
                st.write(f"- **Cumulative CGPA:** {career.get('cgpa')} / 10.0")
                st.write(f"- **Backlog History:** {career.get('backlogs')} active/past")
                st.write(f"- **DSA Problems Solved:** {career.get('dsa_problems_solved')}")
                st.write(f"- **Internships:** {career.get('internships')}")
                st.write(f"- **Placement Status:** **{career.get('placement_status')}**")
                st.write(f"- **Company Type:** {career.get('company_type')}")
                st.write(f"- **Salary Offered:** ₹{career.get('salary_lpa')} LPA")
