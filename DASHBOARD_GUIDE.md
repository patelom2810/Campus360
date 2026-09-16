# Campus360 Dashboard: Comprehensive Visual Analytics & Feature Guide

> **Platform:** Campus360 (KDAC-3)  
> **Purpose:** Student Academic Success, Predictive Early-Warning, and Career Readiness Analytics Cockpit  
> **Tech Stack:** Python 3.11/3.14, Streamlit, Plotly Express/Graph Objects, SQLite/PostgreSQL, Scikit-Learn, Google Gemini, Groq Cloud  
> **Access URL:** `http://localhost:8501`

---

## 1. Executive Overview & Design System

The **Campus360 Dashboard** is an enterprise-grade academic decision-support platform designed for university deans, department chairs, faculty mentors, and placement officers. It synthesizes **10,000 multi-source student records** across 6 departmental silos into **9 dedicated analytical tabs**, featuring interactive visualizations, zero-leakage machine learning forecasts, and real-time Generative AI faculty counseling briefings.

### 🎨 Color Palette & Visual Semantics
The dashboard adheres to a curated, high-contrast institutional design system:
* **Deep Space Blue (`#003049`)**: Primary typography, headers, metric accents, and executive borders.
* **Steel Blue (`#669BBC`)**: Secondary sub-headers, informative text, and interactive focus states.
* **Sunshine Amber (`#FCBF49`)**: Average grade bands, warning boundaries, and moderate metrics.
* **Emerald Cyan / Mint (`#2A9D8F` / `#166534` / `#F0FDF4`)**: Safe, on-track, good, and excellent classifications.
* **Crimson Red (`#C1121F` / `#780000` / `#FDF0D5`)**: High-priority at-risk student warnings and academic probation flags.
* **Vibrant Rainbow Spectrum**: Multi-class categorical charts across performance bands and career domains.

---

## 2. Global Sidebar Filters & Top Executive KPI Banner

### 2.1 Sidebar Controls (Global Dynamic Filtering)
Located in the left sidebar, these controls dynamically cross-filter data across **Tabs 1 through 4**:

| Filter Component | Type | Options / Scope | Impact on Dashboard |
| :--- | :--- | :--- | :--- |
| **Performance Band** | Multi-Select | `Excellent`, `Good`, `Average`, `At_Risk` | Filters all cohort statistics by historical academic standing. |
| **At-Risk Status** | Radio Buttons | • All Students<br>• At-Risk Only (`Flag=1`)<br>• Not At-Risk (`Flag=0`) | Isolates vulnerable students requiring faculty triage. |
| **Preferred Domain** | Multi-Select | `AI/ML`, `Core Engineering`, `Cybersecurity`, `Data Science`, `Product/Management`, `Software Development`, `Web Development` | Slices student metrics by career specialization. |
| **Warehouse Metadata** | Info Badge | Displays active DB engine (`SQLite / warehouse.db`) and total indexed cohort size (`10,000`). |

---

### 2.2 Top Executive KPI Metrics Banner
Positioned at the top of the main dashboard viewport, providing real-time executive summaries:

```
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ FILTERED STUDENTS│   AVERAGE CGPA   │ AT-RISK PROPORTION│  AVG ATTENDANCE  │AVG NEXT SEM MARKS│
│      10,000      │   6.92 / 10.0    │  50.1% (+0.1%)   │      75.8%       │   50.9 / 100     │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

1. **Filtered Students**: Active student count currently displayed based on sidebar filters.
2. **Average CGPA**: Mean cumulative grade point average (scale 0.0 to 10.0).
3. **At-Risk Proportion**: Percentage of active students flagged as at-risk, with delta variance vs. baseline.
4. **Avg Attendance**: Mean biometric/classroom attendance rate across the active subset.
5. **Avg Next Sem Marks**: Projected average examination marks (scale 0 to 100).

---

## 3. Tab-by-Tab Visual Analytics & Feature Breakdown

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       9-TAB DASHBOARD NAVIGATION                                       │
├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┤
│ 1. Grades    │ 2. At-Risk   │ 3. Lifestyle │ 4. Career    │ 5. Student360│ 6. Batch CSV │ 7. ETL & DB  │
│ 8. ML Models │ 9. Simulator │              │              │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

---

### 📊 Tab 1: Performance & Grade Distribution

**Objective:** Institutional grade monitoring, cohort distribution tracking, and assessment component parity.

```
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│  Chart 1.1: Grade Band Distribution (Donut)  │  Chart 1.2: Next Sem Marks (Histogram + KDE) │
│                                              │                                              │
│         [ Excellent: 15% | Good: 35% ]       │       |               __                     │
│         [ Average: 30%   | At-Risk: 20%]     │       |              /  \                    │
│                                              │       |________/\___/____\________           │
│                                              │       0       25    50    75    100          │
├──────────────────────────────────────────────┴──────────────────────────────────────────────┤
│  Chart 1.3: Component Assessment Breakdown (Internal, Assignment, Midterm, Target Marks)    │
│  [==========================] Internal Exam Marks (Mean: 24.8 / 30)                         │
│  [====================] Assignment Score (Mean: 19.2 / 25)                                  │
│  [==============================] Midterm Marks (Mean: 28.5 / 40)                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Visualizations:
* **Chart 1.1 — Academic Performance Band Distribution (Donut Chart)**
  * **Type:** Interactive Plotly Donut Pie Chart with central cutout.
  * **Segments:** `Excellent` (Royal Blue), `Good` (Emerald Cyan), `Average` (Sunshine Yellow), `At_Risk` (Vibrant Red).
  * **Insight:** Instant visual breakdown of cohort health and proportion of struggling vs. honors students.
* **Chart 1.2 — Next Semester Predicted Marks Distribution (Histogram)**
  * **Type:** Plotly Histogram with 30 bins and Kernel Density Estimation (KDE) curve.
  * **X-Axis:** `next_semester_marks` (0 to 100) | **Y-Axis:** Student Count.
  * **Insight:** Displays academic distribution skewness and identifies bimodal performance clustering.
* **Chart 1.3 — Assessment Component Comparison (Categorical Bar Chart)**
  * **Type:** Plotly Bar Chart comparing departmental evaluation components.
  * **Metrics:** Internal Exam Score, Assignment Submission Score, Midterm Score, and Target Next Semester Marks.
  * **Insight:** Highlights whether low performance stems from continuous assignments or high-stakes midterm exams.

---

### ⚠️ Tab 2: At-Risk Early Warning System

**Objective:** Proactive risk detection, vulnerability diagnosis, and high-risk mentee triage.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Section 2.1: Key Risk Drivers & Vulnerability Thresholds                                    │
│  • Sleep < 5.5 hrs/night  • Attendance < 70%  • Backlogs >= 1  • Wellness < 45/100           │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Chart 2.2: Normalized Attribute Comparison: At-Risk vs. Safe Cohorts (Grouped Bar)         │
│                                                                                             │
│  Attendance %      [ Safe: 84% ] [ At-Risk: 62% ]                                           │
│  Study Hours/Day   [ Safe: 4.8 ] [ At-Risk: 2.1 ]                                           │
│  Wellness Score    [ Safe: 78  ] [ At-Risk: 38  ]                                           │
│  Stress Level      [ Safe: 3.4 ] [ At-Risk: 7.9 ]                                           │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Table 2.3: High-Priority At-Risk Student Action Registry                                   │
│  • Searchable, Paginated Table with Student ID, CGPA, Attendance %, Risk Flag, and Actions. │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Visualizations:
* **Component 2.1 — Risk Dimension Metric Cards**
  * Displays high-risk cohort size, average stress score among at-risk students, and mean attendance drop.
* **Chart 2.2 — At-Risk vs. Safe Students Feature Contrast (Grouped Comparison Bar Chart)**
  * **Type:** Bi-color grouped bar chart comparing Safe (`Flag=0`, Green) vs. At-Risk (`Flag=1`, Red) students.
  * **Attributes:** Attendance %, Daily Study Hours, Daily Screen Time, Sleep Hours, Stress Level, Wellness Score.
  * **Insight:** Proves that at-risk status is heavily driven by lifestyle fragility (high stress, low sleep) rather than just raw academic aptitude.
* **Component 2.3 — High-Risk Student Action Registry**
  * **Type:** Interactive Streamlit DataFrame with color highlights on students with active backlogs and low attendance.

---

### 🧠 Tab 3: Lifestyle & Mental Health vs Performance

**Objective:** Correlate non-academic leading indicators (sleep, screen time, stress) with academic outcomes.

```
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│  Chart 3.1: Daily Study vs. Next Sem Marks   │  Chart 3.2: Sleep Duration vs. CGPA          │
│  (Scatter + OLS Linear Trendline)            │  (Scatter with Performance Band Colors)      │
│                                              │                                              │
│  Marks ^          / Trendline                │  CGPA ^       * * * (7-8 hrs optimal)        │
│        |      *  /                           │       |     * * * * *                        │
│        |    *   /                            │       |   * * (Below 5 hrs: steep drop)      │
│        +-------------> Study Hours           │       +---------------------> Sleep Hours    │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│  Chart 3.3: Screen Time Distribution (Box)   │  Chart 3.4: Stress vs. Wellness Matrix       │
│  Across Performance Bands                    │  (Scatter colored by At-Risk Status)         │
│  [At-Risk: Median 7.2h] > [Honors: 3.8h]     │  High Stress + Low Wellness = High Risk Tiers│
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

#### Detailed Visualizations:
* **Chart 3.1 — Daily Study Hours vs. Next Semester Marks (Scatter with OLS Trendline)**
  * **X-Axis:** `study_hours_daily` (0 to 12 hrs) | **Y-Axis:** `next_semester_marks` (0 to 100).
  * **Overlay:** Ordinary Least Squares (OLS) regression line showing positive yield per study hour.
* **Chart 3.2 — Sleep Hours vs. CGPA (Multi-Category Scatter Plot)**
  * **X-Axis:** `sleep_hours` (0 to 12 hrs) | **Y-Axis:** `cgpa` (0.0 to 10.0).
  * **Insight:** Demonstrates the severe academic drop-off for students sleeping $< 5.5$ hours/night.
* **Chart 3.3 — Daily Screen Time Distribution by Grade Band (Box & Whisker Plot)**
  * **X-Axis:** `performance_band` | **Y-Axis:** `screen_time` (hours/day).
  * **Insight:** Displays median, IQR, and outliers of screen time across grade tiers.
* **Chart 3.4 — Stress Level vs. Wellness Score Correlation (Scatter Plot)**
  * **X-Axis:** `stress_level` (1 to 10) | **Y-Axis:** `wellness_score` (0 to 100).
  * **Color:** Red for At-Risk, Green for On-Track.
  * **Insight:** Pinpoints students in the bottom-right danger quadrant (high stress + low wellness).

---

### 💼 Tab 4: Career & Skill Readiness

**Objective:** Map technical competencies, domain specializations, and placement interview readiness.

```
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│  Chart 4.1: Preferred Career Domains (Bar)   │  Chart 4.2: Primary Career Goals (Pie)       │
│  • AI/ML: 28%       • Web Dev: 22%           │  • Top Tech Tier (FAANG/MNC): 42%            │
│  • Data Science: 18%• Cybersecurity: 14%     │  • Higher Studies / Research: 26%            │
│  • Core Eng: 10%    • Product: 8%            │  • Startup / Founder: 18% | PSU/Gov: 14%     │
├──────────────────────────────────────────────┴──────────────────────────────────────────────┤
│  Table 4.3: Technical Capabilities Matrix by Domain                                         │
│  Domain         | Avg Resume (0-100) | Avg Aptitude (0-100) | Avg Projects | Avg Hackathons│
│  AI/ML          |       78.4         |        81.2          |     3.8      |      2.4      │
│  Cybersecurity  |       72.1         |        75.6          |     2.9      |      1.8      │
│  Web Dev        |       74.5         |        72.0          |     4.2      |      2.1      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Visualizations:
* **Chart 4.1 — Preferred Technology Domains (Ranked Vertical Bar Chart)**
  * **X-Axis:** Technical Domain | **Y-Axis:** Student Enrollment Count.
* **Chart 4.2 — Primary Career Objectives (Pie Chart)**
  * Categorizes students by long-term aspiration (e.g. Higher Studies, Tier-1 Tech Placement, Startups).
* **Table 4.3 — Domain Technical Capabilities Matrix (Summary Aggregate Table)**
  * Aggregates Resume Score, Aptitude Score, Communication Score, Project Count, and Hackathons.

---

### 👤 Tab 5: Single Student 360 Dossier

**Objective:** Comprehensive individual student drill-down, 360-degree profiling, and GenAI faculty briefing generation.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Section 5.1: 1-Click Quick Preset Profiles                                                 │
│  [ 🎲 Random Student ] [ ⚠️ S100000 (High Risk) ] [ ⚠️ S100001 (Fragile) ] [ ✅ S100004 (Safe) ]│
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 5.2: Smart Search Bar (Supports 'S100900', 'S900', or numeric shorthand '900')      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 5.3: 3-Column Unified Dossier                                                       │
│  ┌─────────────────────────┬─────────────────────────┬───────────────────────────────────┐  │
│  │ Column 1: Identity      │ Column 2: Academics     │ Column 3: Lifestyle & Skills      │  │
│  │ • Avatar & Student ID   │ • CGPA: 4.82 / 10.0     │ • Daily Study: 1.5 hrs            │  │
│  │ • Risk Badge (HIGH RISK)│ • Backlogs: 2 Active    │ • Sleep: 4.2 hrs/night            │  │
│  │ • Enrollment Date       │ • Attendance: 58.2%     │ • Stress: 8.5/10 | Wellness: 32   │  │
│  │ • Domain & Goal         │ • Predicted Marks: 38.5 │ • Repos: 1 | Resume: 42/100       │  │
│  └─────────────────────────┴─────────────────────────┴───────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 5.4: On-Demand GenAI Faculty Advisory Briefing                                     │
│  [ ✨ Generate AI Faculty Briefing for S100000 ]                                             │
│  --> Generates 4-part structured briefing (Executive Assessment, Root Causes, Strengths,   │
│      14-Day Intervention Plan) using Google Gemini 3.6 Flash with Groq fallback.            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 📁 Tab 6: Predict from CSV & Batch Inference

**Objective:** Batch model inference on unlabelled/new cohorts, automated data validation, and faculty intervention triage.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Section 6.1: Sample CSV Template Generator [ 📥 Download Sample CSV Template ]             │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 6.2: Option A — Load Pre-Built Realistic Cohort Batches (Dropdown)                 │
│  • Batch 1: High Risk & Academic Probation Cohort (30 Students)                             │
│  • Batch 2: Honors & Placement Star Candidates (30 Students)                                │
│  • Batch 3: Borderline Attendance & Stress Boundary Cases (30 Students)                      │
│  • Batch 4: Balanced Classroom Cohort Section (40 Students)                                 │
│  • Batch 5: Final Year Career & Placement Batch (30 Students)                               │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 6.3: Option B — Drag & Drop Custom CSV Upload                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 6.4: Automated Data Quality Validation & Mean Imputation Engine                    │
│  • Scans for missing columns and invalid non-numeric inputs.                                │
│  • Offers interactive resolution: (1) Drop invalid rows, or (2) Mean-impute missing values. │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 6.5: Batch ML Predictions Table with Risk Highlighter                              │
│  • Appends 'predicted_next_sem_marks', 'predicted_risk_prob', and 'risk_classification'.    │
│  • Radio Filter: [ All Students | At-Risk Only (High Priority) | On-Track Only ]            │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 6.6: Faculty Mentor Early Intervention Action Panel                                │
│  • Select any at-risk student from batch -> Click [ Generate AI Mentor Response ]           │
│  • Produces instant, targeted mentoring advice tailored to that batch record.               │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 6.7: Export [ 📥 Download Predictions CSV ]                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 🏗️ Tab 7: ETL Pipeline & Data Warehouse Architecture

**Objective:** Data engineering transparency, departmental reconciliation audit, and database schema inspection.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Section 7.1: Top Architecture Metrics Cards                                                │
│  • 6 Feeds Ingested • 10,000 Master Students • 100.0% Key Match Rate • 7 Tables + 4 Views   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 7.2: 5-Stage Visual Architecture Cards                                             │
│  [ 1. Extract ] -> [ 2. Transform ] -> [ 3. Stitch ] -> [ 4. Load & DDL ] -> [ 5. Validate ]│
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 7.3: Departmental Data Sources & Key Reconciliation Audit Table                    │
│  Source File                | Department | Original Key | Raw Rows | Stitched IDs | Match % │
│  1_student_records.csv      | Registrar  | student_id   |  10,080  |    10,000    |  100.0% │
│  2_exam_marks.csv           | Exams      | StudentID    |  10,050  |    10,000    |  100.0% │
│  3_attendance.csv           | LMS        | roll_no      |  10,100  |    10,000    |  100.0% │
│  4_lifestyle.csv            | Wellness   | student_id   |  10,060  |    10,000    |  100.0% │
│  5_skills.csv               | Placement  | STUDENT_ID   |  10,070  |    10,000    |  100.0% │
│  6_career_preferences.csv   | Career Off | roll_number  |  10,050  |    10,000    |  100.0% │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 7.4: Automated 5-Dimension Quality Verification Badges (All PASS)                  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 7.5: Relational Warehouse Schema & Table Inspector (Live Table Previews)           │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 🤖 Tab 8: Model Architecture & Accuracy Diagnostics

**Objective:** Machine learning auditability, hyperparameter benchmark reports, and zero-leakage verification.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Section 8.1: Dual ML Pipeline Overview & Zero Target Leakage Guarantee                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 8.2: Model 1 — Next Semester Marks Regressor (Random Forest)                       │
│  • R² Score: ~0.84 | RMSE: ~4.12 | MAE: ~3.25                                               │
│  • Hyperparameter Tuning Table: Grid search comparison of 6 candidate configurations.      │
│  • Chart 8.2: Feature Importance Bar Chart (Top drivers: CGPA, Internal Marks, Study Hrs). │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 8.3: Model 2 — At-Risk Early Warning Classifier (Balanced Random Forest)           │
│  • Screening Recall: ~88.4% (Tuned Threshold: 0.370) | ROC-AUC: ~0.92                       │
│  • Chart 8.3: Classifier Feature Importance (Top drivers: Wellness, Stress, Attendance).   │
│  • Confusion Matrix 1: Calibrated Screening Threshold (0.370) minimizing False Negatives.   │
│  • Confusion Matrix 2: Standard Baseline Threshold (0.50) comparison.                       │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 🎯 Tab 9: Interactive Predictor & AI Guidance

**Objective:** Real-time "what-if" scenario simulation and dynamic faculty counseling synthesis.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Section 9.1: Scenario Simulation Quick-Presets                                             │
│  [ 🚨 High Risk Candidate ] [ ⚖️ Borderline Student ] [ 🌟 Honors Star Candidate ]           │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 9.2: Interactive Feature Sliders (3 Categories)                                    │
│  • Academic Profile: Current CGPA, Previous Semester %, Active Backlogs, Attendance %       │
│  • Lifestyle & Wellness: Daily Study, Sleep Hours, Daily Screen Time, Stress Level (1-10)   │
│  • Career & Skills: Resume Score, Projects Count, GitHub Repos, Hackathons Participated     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 9.3: Real-Time Model Forecast                                                      │
│  • Predicted Next Semester Marks: 74.2 / 100 (Gauge / Metric)                               │
│  • Predicted Risk Probability: 14.8%                                                        │
│  • Risk Badge: [ LOW RISK / ON TRACK ]                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  Section 9.4: Instant Faculty AI Mentorship Briefing                                        │
│  • Synthesizes live slider values into an immediate 4-part faculty counseling roadmap.      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Operational Playbooks: How Stakeholders Use Campus360

### 🏛️ 1. Academic Deans & Department Chairs
* **Primary Tabs:** **Tab 1 (Grades)**, **Tab 2 (At-Risk)**, **Tab 7 (ETL Architecture)**.
* **Workflow:**
  1. Inspect the top KPI banner for overall student risk rates.
  2. Filter by department to identify curriculum subjects with abnormal failure rates.
  3. Review the ETL audit to ensure all SIS and examination feeds are 100% reconciled.

### 👨‍🏫 2. Faculty Advisors & Mentors
* **Primary Tabs:** **Tab 5 (Student 360 Dossier)**, **Tab 6 (Batch CSV)**, **Tab 9 (Interactive Predictor)**.
* **Workflow:**
  1. Open **Tab 5** and type the student's ID (e.g. `S100000` or shorthand `900`).
  2. Click **"✨ Generate AI Faculty Briefing"** before the 1-on-1 counseling session.
  3. Use **Tab 9** with the student to simulate how increasing sleep by 2 hours and study by 1 hour improves their projected grades.

### 💼 3. Placement & Career Cell Officers
* **Primary Tabs:** **Tab 4 (Career Readiness)**, **Tab 6 (Predict from CSV)**.
* **Workflow:**
  1. Filter by tech domain (e.g. `AI/ML` or `Cybersecurity`) in **Tab 4**.
  2. Identify students with high aptitude but low resume scores for targeted resume workshops.
  3. Upload final-year batch CSVs in **Tab 6** to screen students needing remediation before placement drives.

### 🔬 4. Data Science & Technical Evaluators
* **Primary Tabs:** **Tab 7 (ETL & Warehouse)**, **Tab 8 (Model Architecture & Accuracy)**.
* **Workflow:**
  1. Verify zero target leakage in feature selection views.
  2. Inspect Model 1 & Model 2 hyperparameter tuning logs and feature importance plots.
  3. Confirm the calibrated screening threshold ($0.370$) designed specifically to maximize high-risk recall ($\ge 85\%$).

---

## 5. Verification & Troubleshooting

* **Dashboard URL:** `http://localhost:8501`
* **Restarting the Platform:**
  ```bash
  docker compose down && docker compose up -d
  ```
* **Running Quality Checks Inside Docker:**
  ```bash
  docker exec campus360_app python /app/etl/validate.py
  ```
* **Running Local Automated Tests:**
  ```bash
  python -m unittest discover -s tests
  ```
