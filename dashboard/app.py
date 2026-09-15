"""
Campus360 — Executive Student Analytics & Early Warning Dashboard
Streamlit-powered interactive analytics platform powered by the SQLite Warehouse.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Ensure project root is in python path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import get_db_connection, WAREHOUSE_DB_PATH

# ── Page Configuration & Theming ──────────────────────────────────────────────
st.set_page_config(
    page_title="Campus360 | Student Analytics & Early Warning Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished aesthetics
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E1B4B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .risk-badge {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .safe-badge {
        background-color: #DCFCE7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load_data():
    """Loads student master view data from the SQLite warehouse."""
    conn = get_db_connection()
    try:
        # Check if student_360_view exists, fallback to student_master_stitched
        query = "SELECT * FROM student_360_view;"
        df = pd.read_sql_query(query, conn)
    except Exception:
        query = "SELECT * FROM student_master_stitched;"
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return df


df = load_data()

# ── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=64)
    st.markdown("## **Campus360**")
    st.caption("AI-Powered Student Success Engine")
    st.markdown("---")

    # Global Filters
    st.markdown("### 🔍 Filters")

    all_bands = sorted([b for b in df["performance_band"].dropna().unique()])
    selected_bands = st.multiselect(
        "Performance Band",
        options=all_bands,
        default=all_bands,
    )

    risk_filter = st.radio(
        "At-Risk Status",
        options=["All Students", "At-Risk Only (Flag=1)", "Not At-Risk (Flag=0)"],
        index=0,
    )

    all_domains = sorted([d for d in df["preferred_domain"].dropna().unique()])
    selected_domains = st.multiselect(
        "Preferred Domain",
        options=all_domains,
        default=all_domains,
    )

    st.markdown("---")
    st.info(f"**Warehouse:** SQLite ({WAREHOUSE_DB_PATH.name})\n**Total Cohort:** {len(df):,} students")

# ── Apply Filtering ───────────────────────────────────────────────────────────
filtered_df = df.copy()
if selected_bands:
    filtered_df = filtered_df[filtered_df["performance_band"].isin(selected_bands)]

if risk_filter == "At-Risk Only (Flag=1)":
    filtered_df = filtered_df[filtered_df["at_risk_flag"] == 1]
elif risk_filter == "Not At-Risk (Flag=0)":
    filtered_df = filtered_df[filtered_df["at_risk_flag"] == 0]

if selected_domains:
    filtered_df = filtered_df[filtered_df["preferred_domain"].isin(selected_domains)]

# ── Header & KPI Metrics ──────────────────────────────────────────────────────
st.markdown('<div class="main-header">🎓 Campus360 Student Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-header">Holistic Student Performance, Psychological Wellness, and Early Screening Insights · Showing <b>{len(filtered_df):,}</b> of <b>{len(df):,}</b> students</div>',
    unsafe_allow_html=True,
)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
total_count = len(filtered_df)
avg_cgpa = filtered_df["cgpa"].mean() if total_count > 0 else 0
risk_rate = (filtered_df["at_risk_flag"].mean() * 100) if total_count > 0 else 0
avg_attendance = filtered_df["attendance_percentage"].mean() if total_count > 0 else 0
avg_marks = filtered_df["next_semester_marks"].mean() if total_count > 0 else 0

kpi1.metric("Filtered Students", f"{total_count:,}")
kpi2.metric("Average CGPA", f"{avg_cgpa:.2f} / 10.0")
kpi3.metric("At-Risk Proportion", f"{risk_rate:.1f}%", delta=f"{risk_rate - 50.0:+.1f}% vs baseline", delta_color="inverse")
kpi4.metric("Avg Attendance", f"{avg_attendance:.1f}%")
kpi5.metric("Avg Next Sem Marks", f"{avg_marks:.1f} / 100")

st.markdown("---")

# ── Tabs Navigation ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Performance & Grade Bands",
    "At-Risk Early Warning",
    "Lifestyle & Mental Health",
    "Career & Skill Readiness",
    "Individual Student 360",
    "Predict from CSV",
])

# ── TAB 1: Performance & Grade Distribution ───────────────────────────────────
with tab1:
    st.subheader("Subject Exam Marks & Academic Performance Distribution")
    col1, col2 = st.columns(2)

    with col1:
        band_counts = filtered_df["performance_band"].value_counts().reset_index()
        band_counts.columns = ["Band", "Students"]
        color_map = {
            "Excellent": "#10B981",
            "Good": "#3B82F6",
            "Average": "#F59E0B",
            "At_Risk": "#EF4444",
        }
        fig_band = px.pie(
            band_counts,
            names="Band",
            values="Students",
            title="Academic Performance Band Distribution",
            color="Band",
            color_discrete_map=color_map,
            hole=0.45,
        )
        fig_band.update_traces(textinfo="percent+label", textposition="inside")
        st.plotly_chart(fig_band, use_container_width=True)

    with col2:
        fig_hist = px.histogram(
            filtered_df,
            x="next_semester_marks",
            color="performance_band",
            color_discrete_map=color_map,
            nbins=30,
            title="Next Semester Marks Distribution by Band",
            marginal="box",
        )
        fig_hist.update_layout(xaxis_title="Next Semester Marks (Target)", yaxis_title="Number of Students")
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("#### Exam Component Comparison")
    exam_cols = [
        "previous_internal_marks",
        "previous_assignment_score",
        "previous_midterm_score",
        "lowest_subject_score",
        "next_semester_marks",
    ]
    exam_summary = filtered_df[exam_cols].mean().reset_index()
    exam_summary.columns = ["Assessment Component", "Cohort Average"]
    exam_summary["Assessment Component"] = exam_summary["Assessment Component"].str.replace("_", " ").str.title()

    fig_bar = px.bar(
        exam_summary,
        x="Assessment Component",
        y="Cohort Average",
        text_auto=".1f",
        color="Cohort Average",
        color_continuous_scale="Viridis",
        title="Average Component Exam Scores Across Cohort",
    )
    fig_bar.update_layout(yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_bar, use_container_width=True)

# ── TAB 2: At-Risk Early Warning System ───────────────────────────────────────
with tab2:
    st.subheader("At-Risk Student Screening & Critical Factors")
    st.markdown(
        """
        Students identified as **At-Risk (`at_risk_flag = 1`)** require early intervention.
        Key drivers identified by **Model 2 (At-Risk Classifier)** include:
        **Low Wellness Score**, **Elevated Stress**, **Drop in Motivation**, and **High Screen-to-Study Ratio**.
        """
    )

    at_risk_subset = filtered_df[filtered_df["at_risk_flag"] == 1]
    safe_subset = filtered_df[filtered_df["at_risk_flag"] == 0]

    rcol1, rcol2, rcol3 = st.columns(3)
    rcol1.metric("Flagged At-Risk Students", f"{len(at_risk_subset):,}", f"{(len(at_risk_subset)/max(1, len(filtered_df))*100):.1f}% of current view")
    rcol2.metric("At-Risk Avg Wellness", f"{at_risk_subset['wellness_score'].mean():.1f} / 100" if len(at_risk_subset) else "N/A", delta=f"{at_risk_subset['wellness_score'].mean() - safe_subset['wellness_score'].mean():.1f} vs safe", delta_color="normal")
    rcol3.metric("At-Risk Avg Stress", f"{at_risk_subset['stress_level'].mean():.1f} / 10" if len(at_risk_subset) else "N/A", delta=f"{at_risk_subset['stress_level'].mean() - safe_subset['stress_level'].mean():+.1f} vs safe", delta_color="inverse")

    # Risk Drivers Comparison Chart
    factors = ["wellness_score", "burnout_score", "attendance_percentage", "assignment_completion_rate", "cgpa"]
    comparison_data = []
    for f in factors:
        comparison_data.append({
            "Factor": f.replace("_", " ").title(),
            "At-Risk Cohort": round(float(at_risk_subset[f].mean() if len(at_risk_subset) else 0), 2),
            "Not At-Risk Cohort": round(float(safe_subset[f].mean() if len(safe_subset) else 0), 2),
        })
    comp_df = pd.DataFrame(comparison_data)

    fig_comp = go.Figure(data=[
        go.Bar(name="At-Risk Students", x=comp_df["Factor"], y=comp_df["At-Risk Cohort"], marker_color="#EF4444"),
        go.Bar(name="Not At-Risk Students", x=comp_df["Factor"], y=comp_df["Not At-Risk Cohort"], marker_color="#10B981"),
    ])
    fig_comp.update_layout(barmode="group", title="Holistic Metrics: At-Risk vs. Non At-Risk Students")
    st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("#### High-Risk Student Action Registry")
    display_cols = [
        "student_id", "cgpa", "backlogs", "attendance_percentage",
        "wellness_score", "stress_level", "motivation_level", "previous_cgpa", "preferred_domain"
    ]
    st.dataframe(
        at_risk_subset[display_cols].sort_values(by=["cgpa", "wellness_score"], ascending=[True, True]).head(100),
        use_container_width=True,
        hide_index=True,
    )

# ── TAB 3: Lifestyle & Mental Health vs Performance ───────────────────────────
with tab3:
    st.subheader("Lifestyle Factors vs. Academic Performance")
    lcol1, lcol2 = st.columns(2)

    with lcol1:
        fig_study = px.scatter(
            filtered_df.sample(min(1000, len(filtered_df)), random_state=42) if len(filtered_df) > 1000 else filtered_df,
            x="study_hours_daily",
            y="next_semester_marks",
            color="at_risk_flag",
            color_discrete_map={0: "#10B981", 1: "#EF4444"},
            labels={"study_hours_daily": "Daily Study Hours", "next_semester_marks": "Next Semester Marks", "at_risk_flag": "At-Risk"},
            title="Daily Study Hours vs. Next Semester Marks (Sample)",
            trendline="ols" if HAS_STATSMODELS else None,
        )
        st.plotly_chart(fig_study, use_container_width=True)

    with lcol2:
        fig_sleep = px.scatter(
            filtered_df.sample(min(1000, len(filtered_df)), random_state=42) if len(filtered_df) > 1000 else filtered_df,
            x="sleep_hours",
            y="cgpa",
            color="stress_level",
            color_continuous_scale="Reds",
            labels={"sleep_hours": "Sleep Hours / Night", "cgpa": "Current CGPA", "stress_level": "Stress"},
            title="Sleep Hours vs. CGPA (Colored by Stress Level)",
        )
        st.plotly_chart(fig_sleep, use_container_width=True)

    lcol3, lcol4 = st.columns(2)
    with lcol3:
        fig_screen = px.box(
            filtered_df,
            x="performance_band",
            y="screen_time",
            color="performance_band",
            color_discrete_map=color_map,
            title="Daily Screen Time by Performance Band",
        )
        st.plotly_chart(fig_screen, use_container_width=True)

    with lcol4:
        fig_wellness = px.scatter(
            filtered_df.sample(min(1000, len(filtered_df)), random_state=42) if len(filtered_df) > 1000 else filtered_df,
            x="stress_level",
            y="burnout_score",
            color="at_risk_flag",
            color_discrete_map={0: "#10B981", 1: "#EF4444"},
            title="Stress Level vs. Burnout Score",
            trendline="ols" if HAS_STATSMODELS else None,
        )
        st.plotly_chart(fig_wellness, use_container_width=True)

# ── TAB 4: Career & Skill Readiness ───────────────────────────────────────────
with tab4:
    st.subheader("Career Goals, Domain Interests & Technical Readiness")
    ccol1, ccol2 = st.columns(2)

    with ccol1:
        domain_counts = filtered_df["preferred_domain"].value_counts().reset_index()
        domain_counts.columns = ["Domain", "Students"]
        fig_domain = px.bar(
            domain_counts,
            x="Students",
            y="Domain",
            orientation="h",
            text_auto=True,
            color="Students",
            color_continuous_scale="Blues",
            title="Student Distribution Across Preferred Domains",
        )
        fig_domain.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_domain, use_container_width=True)

    with ccol2:
        goal_counts = filtered_df["career_goal"].value_counts().reset_index()
        goal_counts.columns = ["Career Goal", "Count"]
        fig_goal = px.pie(
            goal_counts,
            names="Career Goal",
            values="Count",
            title="Primary Career Objectives",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        st.plotly_chart(fig_goal, use_container_width=True)

    st.markdown("#### Technical Capabilities by Career Domain")
    domain_skills = filtered_df.groupby("preferred_domain").agg({
        "resume_score": "mean",
        "aptitude_score": "mean",
        "communication_skills": "mean",
        "development_projects_count": "mean",
        "hackathons_participated": "mean",
    }).round(2).reset_index()

    domain_skills.columns = [
        "Preferred Domain", "Avg Resume", "Avg Aptitude", "Avg Communication",
        "Avg Projects", "Avg Hackathons"
    ]
    st.dataframe(domain_skills, use_container_width=True, hide_index=True)

# ── TAB 5: Individual Student 360 Deep-Dive ───────────────────────────────────
with tab5:
    st.subheader("Single Student 360 Dossier")

    from genai.generate_insights import normalize_student_id

    # 1-Click Quick Preset Profiles
    st.markdown("##### ⚡ Quick Select Preset Profiles:")
    pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns(5)

    if "selected_student_id" not in st.session_state:
        st.session_state["selected_student_id"] = "S100000"

    if pcol1.button("🎲 Random Student"):
        st.session_state["selected_student_id"] = str(df["student_id"].sample(1).iloc[0])
    if pcol2.button("⚠️ At-Risk Example (S100000)"):
        st.session_state["selected_student_id"] = "S100000"
    if pcol3.button("⚠️ Academic Fragile (S100001)"):
        st.session_state["selected_student_id"] = "S100001"
    if pcol4.button("✅ Low-Risk Example (S100004)"):
        st.session_state["selected_student_id"] = "S100004"
    if pcol5.button("🎯 Student S900 (S100900)"):
        st.session_state["selected_student_id"] = "S100900"

    raw_input = st.text_input(
        "Enter Student ID or Number (e.g. S100900, S900, 900, S100000):",
        value=st.session_state["selected_student_id"],
        help="You can enter full ID (S100900), short form (S900), or simple number (900)."
    ).strip().upper()

    # Smart ID resolution (handles S900, 900, S100000, etc.)
    resolved_id = normalize_student_id(raw_input)
    all_known_ids = set(df["student_id"].dropna().unique())

    if resolved_id in all_known_ids:
        search_id = resolved_id
        if resolved_id != raw_input:
            st.info(f"💡 Resolved shorthand '**{raw_input}**' to Student ID **{resolved_id}**")
    else:
        search_id = raw_input

    student_records = df[df["student_id"] == search_id]
    if student_records.empty:
        # Check partial/fuzzy substring matches
        partial_matches = [sid for sid in all_known_ids if raw_input in sid]
        if partial_matches:
            st.warning(f"Student ID '{raw_input}' not found directly. Did you mean one of these?")
            search_id = st.selectbox("Matching student IDs in warehouse:", options=sorted(partial_matches)[:20])
            student_records = df[df["student_id"] == search_id]
        else:
            st.error(f"Student ID '{raw_input}' not found in the warehouse. Valid IDs range from **S100000** to **S109999** (or enter 0 to 9999).")

    if not student_records.empty:
        s = student_records.iloc[0]
        s_col1, s_col2, s_col3 = st.columns([1, 2, 2])

        with s_col1:
            st.image("https://img.icons8.com/fluency/96/user-male-circle.png", width=90)
            st.markdown(f"### **{s['student_id']}**")
            if s["at_risk_flag"] == 1:
                st.markdown('<span class="risk-badge">⚠️ HIGH RISK STUDENT</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="safe-badge">✅ LOW RISK / ON TRACK</span>', unsafe_allow_html=True)
            st.markdown(f"**Enrolled:** {s.get('enrollment_date', 'N/A')}")
            st.markdown(f"**Domain:** {s.get('preferred_domain', 'N/A')}")
            st.markdown(f"**Goal:** {s.get('career_goal', 'N/A')}")

        with s_col2:
            st.markdown("#### 🎓 Academic Profile")
            st.write(f"- **Current CGPA:** `{s['cgpa']}` / 10.0")
            st.write(f"- **Previous CGPA:** `{s['previous_cgpa']}`")
            st.write(f"- **Active Backlogs:** `{s['backlogs']}`")
            st.write(f"- **Attendance:** `{s['attendance_percentage']}%`")
            st.write(f"- **Predicted Next Sem Marks:** `{s['next_semester_marks']}` / 100")
            st.write(f"- **Performance Band:** `{s['performance_band']}`")

        with s_col3:
            st.markdown("#### 🏃 Lifestyle & Skills")
            st.write(f"- **Daily Study:** `{s['study_hours_daily']} hrs`")
            st.write(f"- **Sleep Hours:** `{s['sleep_hours']} hrs/night`")
            st.write(f"- **Wellness Score:** `{s['wellness_score']} / 100`")
            st.write(f"- **Stress Level:** `{s['stress_level']} / 10`")
            st.write(f"- **Resume Score:** `{s['resume_score']} / 100`")
            st.write(f"- **GitHub Repos:** `{s['git_hub_repos']}` | **Projects:** `{s['development_projects_count']}`")

        st.markdown("---")
        st.markdown("### 🤖 Faculty AI Advisory Briefing")
        st.caption("Powered by Gemini 3.6 Flash (with Groq Qwen 3.8 fallback) & Campus360 ML Models")

        if st.button("✨ Generate AI Faculty Briefing for " + search_id, type="primary"):
            with st.spinner("Analyzing student dossier and generating academic counseling summary..."):
                try:
                    from genai.generate_insights import generate_student_insight
                    insight_res = generate_student_insight(search_id)
                    st.success(f"Generated via {insight_res['provider']} ({insight_res['model']})")
                    st.markdown(insight_res["insights"])
                except Exception as ex:
                    st.error(f"Failed to generate insight: {ex}")

# ── TAB 6: Predict from CSV (Batch Inference) ──────────────────────────────────
with tab6:
    st.subheader("📂 Batch Student Inference: Predict from CSV")
    st.markdown(
        """
        Upload a batch of student records (`.csv`) to generate dual ML predictions:
        * **Model 1 (Regression):** `predicted_next_sem_marks` (Continuous score forecast)
        * **Model 2 (Classification):** `predicted_risk_prob` & `risk_classification` (Calibrated threshold = 0.416)
        """
    )

    import joblib
    from config.config import MODEL_1_PATH, MODEL_2_PATH
    from genai.generate_insights import predict_batch, get_ml_predictions

    # 1. Load feature registry directly from trained model artifacts
    if not MODEL_1_PATH.exists() or not MODEL_2_PATH.exists():
        st.error("❌ Model artifacts (`next_semester_marks_model.pkl` or `at_risk_classifier_model.pkl`) not found in models/.")
    else:
        m1_obj = joblib.load(MODEL_1_PATH)
        m2_obj = joblib.load(MODEL_2_PATH)
        m1_required = list(getattr(m1_obj, "feature_names_in_", []))
        m2_required = list(getattr(m2_obj, "feature_names_in_", []))

        # Union of required features
        all_required = list(dict.fromkeys(m1_required + m2_required))

        # Sample Template Download Helper
        with st.expander("ℹ️ Download Sample CSV Template & Required Column Specifications"):
            st.markdown(
                f"**Required Feature Union ({len(all_required)} unique columns):**\n"
                f"* **Model 1 (18 features):** `{', '.join(m1_required)}`\n"
                f"* **Model 2 (26 features):** `{', '.join(m2_required)}`\n\n"
                f"*(Note: `backlogs` and `backlog_history` are seamlessly mapped. Extra columns like `student_id` or names are safely preserved).* "
            )
            template_cols = [c for c in ["student_id"] + all_required if c in df.columns]
            sample_template_df = df[template_cols].head(5)
            st.download_button(
                label="📄 Download 5-Student Sample CSV Template",
                data=sample_template_df.to_csv(index=False).encode("utf-8"),
                file_name="campus360_predict_template.csv",
                mime="text/csv",
            )

        # 2. Upload CSV
        csv_file = st.file_uploader(
            "Select Student Records CSV file to analyze",
            type=["csv"],
            key="predict_csv_uploader",
            help="Upload a CSV file containing required academic, engagement, and lifestyle attributes.",
        )

        if csv_file is not None:
            try:
                uploaded_raw_df = pd.read_csv(csv_file)
            except Exception as read_err:
                st.error(f"❌ Error parsing CSV file: {read_err}")
                uploaded_raw_df = None

            if uploaded_raw_df is not None:
                st.write(
                    f"**File uploaded:** `{csv_file.name}` | "
                    f"**Rows:** `{len(uploaded_raw_df):,}` | "
                    f"**Columns:** `{len(uploaded_raw_df.columns)}`"
                )

                # 3. Column Validation
                existing_cols = set(uploaded_raw_df.columns)
                missing_features = []

                for req_col in all_required:
                    if req_col not in existing_cols:
                        # Allow interchangeable backlogs / backlog_history
                        if req_col == "backlogs" and "backlog_history" in existing_cols:
                            continue
                        if req_col == "backlog_history" and "backlogs" in existing_cols:
                            continue
                        missing_features.append(req_col)

                if missing_features:
                    st.error(
                        f"❌ **Validation Error — Missing Required Columns ({len(missing_features)}):**\n\n"
                        + ", ".join([f"`{col}`" for col in sorted(missing_features)])
                        + "\n\nPlease ensure your CSV includes all required attributes before prediction."
                    )
                else:
                    # Column validation passed! Extra columns are ignored/preserved.
                    working_df = uploaded_raw_df.copy()

                    # Harmonize backlogs / backlog_history if only one is present
                    if "backlogs" in working_df.columns and "backlog_history" not in working_df.columns:
                        working_df["backlog_history"] = working_df["backlogs"]
                    elif "backlog_history" in working_df.columns and "backlogs" not in working_df.columns:
                        working_df["backlogs"] = working_df["backlog_history"]

                    # 4. Null and Non-Numeric Value Detection across required features
                    invalid_rows_set = set()
                    invalid_details_list = []

                    for feat in all_required:
                        num_series = pd.to_numeric(working_df[feat], errors="coerce")
                        bad_mask = num_series.isna()
                        if bad_mask.any():
                            bad_indices = working_df.index[bad_mask].tolist()
                            invalid_rows_set.update(bad_indices)
                            for r_idx in bad_indices[:15]:
                                invalid_details_list.append({
                                    "Row (1-indexed)": r_idx + 1,
                                    "Column": feat,
                                    "Invalid / Null Value": repr(working_df.at[r_idx, feat]),
                                })

                    ready_to_predict = True
                    clean_input_df = working_df.copy()

                    if invalid_rows_set:
                        st.warning(
                            f"⚠️ **Data Quality Warning:** Found **{len(invalid_rows_set):,} row(s)** "
                            f"with missing or non-numeric values in required feature columns."
                        )
                        with st.expander(f"Inspect First {min(15, len(invalid_details_list))} Affected Cells"):
                            st.dataframe(pd.DataFrame(invalid_details_list), use_container_width=True, hide_index=True)

                        imputation_choice = st.radio(
                            "Choose an automated resolution strategy before running models:",
                            options=[
                                f"Drop rows with invalid values (drop {len(invalid_rows_set):,} rows)",
                                "Fill invalid / missing values with column mean (keep all rows)",
                            ],
                            index=0,
                        )

                        if "Drop" in imputation_choice:
                            clean_input_df = working_df.drop(index=list(invalid_rows_set)).reset_index(drop=True)
                            if clean_input_df.empty:
                                st.error("❌ All rows contained invalid or null values. No valid rows remaining.")
                                ready_to_predict = False
                            else:
                                st.info(f"Proceeding with **{len(clean_input_df):,}** clean rows ({len(invalid_rows_set):,} dropped).")
                        else:
                            clean_input_df = working_df.copy()
                            for feat in all_required:
                                clean_input_df[feat] = pd.to_numeric(clean_input_df[feat], errors="coerce")
                                mean_val = clean_input_df[feat].mean()
                                if pd.isna(mean_val):
                                    mean_val = 0.0
                                clean_input_df[feat] = clean_input_df[feat].fillna(mean_val)
                            st.info("Filled all invalid / missing values with their respective feature means.")
                    else:
                        st.success(f"✅ **Validation Succeeded:** All {len(clean_input_df):,} rows have complete numeric features.")

                    # 5. Run Prediction via predict_batch() / get_ml_predictions()
                    if ready_to_predict:
                        st.markdown("---")
                        if st.button("🚀 Execute Batch Predictions", type="primary"):
                            with st.spinner(f"Computing predictions for {len(clean_input_df):,} students..."):
                                # Reuse get_ml_predictions vectorized batch inference
                                predicted_batch_df = get_ml_predictions(clean_input_df)

                            st.session_state["active_batch_results"] = predicted_batch_df
                            st.success(f"🎉 Generated predictions for {len(predicted_batch_df):,} student records!")

                        # 6. Display results and Export
                        if "active_batch_results" in st.session_state and st.session_state["active_batch_results"] is not None:
                            batch_res = st.session_state["active_batch_results"]

                            pred_cols = ["predicted_next_sem_marks", "predicted_risk_prob", "risk_classification"]
                            front_cols = [c for c in ["student_id"] if c in batch_res.columns] + pred_cols
                            tail_cols = [c for c in batch_res.columns if c not in front_cols]
                            ordered_display_df = batch_res[front_cols + tail_cols]

                            # Summary KPI Metrics
                            total_rows = len(ordered_display_df)
                            at_risk_count = (ordered_display_df["risk_classification"] == "At-Risk (High Priority)").sum()
                            at_risk_pct = (at_risk_count / total_rows * 100) if total_rows > 0 else 0
                            avg_marks = ordered_display_df["predicted_next_sem_marks"].mean() if total_rows > 0 else 0
                            avg_prob = ordered_display_df["predicted_risk_prob"].mean() if total_rows > 0 else 0

                            st.markdown("### 📈 Batch Prediction Summary")
                            k1, k2, k3, k4 = st.columns(4)
                            k1.metric("Evaluated Students", f"{total_rows:,}")
                            k2.metric("Flagged At-Risk", f"{at_risk_count:,} ({at_risk_pct:.1f}%)", delta=f"{at_risk_pct - 50:+.1f}% vs baseline", delta_color="inverse")
                            k3.metric("Avg Predicted Marks", f"{avg_marks:.2f} / 100")
                            k4.metric("Avg Risk Probability", f"{avg_prob:.3f}")

                            st.markdown("### 📋 Prediction Table Preview")

                            def highlight_risk(val):
                                if val == "At-Risk (High Priority)":
                                    return "background-color: #FEE2E2; color: #991B1B; font-weight: bold;"
                                elif val == "On-Track":
                                    return "background-color: #DCFCE7; color: #166534; font-weight: bold;"
                                return ""

                            # Style table cleanly across pandas versions
                            if hasattr(ordered_display_df.style, "map"):
                                styled_df = ordered_display_df.style.map(highlight_risk, subset=["risk_classification"])
                            else:
                                styled_df = ordered_display_df.style.applymap(highlight_risk, subset=["risk_classification"])

                            st.dataframe(styled_df, use_container_width=True)

                            # Download Export Button
                            csv_download_data = batch_res.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="📥 Export Predictions as CSV",
                                data=csv_download_data,
                                file_name=f"campus360_batch_predictions_{csv_file.name}",
                                mime="text/csv",
                                type="primary",
                            )
