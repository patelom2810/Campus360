# Campus360

Campus360 is an end-to-end student academic success, subject performance, and career readiness analytics platform tailored for Indian educational institutions. It integrates academic, behavioral, attendance, skill proficiency, and placement datasets through disciplined data stitching into an enterprise-ready star schema warehouse.

---

## 📁 Folder Structure

```
Campus360/
│
├── data/
│   ├── raw/                                     # Original source files (unmodified)
│   │   ├── career_path_in_all_field.csv         # Career paths across domains
│   │   ├── cs_students.csv                      # CS student skills & domains (180 rows)
│   │   ├── enhanced_student_habits_performance_dataset.csv  # Habits & performance
│   │   ├── hybrid_student_performance_1200.csv  # Student behavioral & risk survey (1,200 rows)
│   │   └── student_lifestyle_dataset.csv        # Student lifestyle data
│   │
│   └── processed/                               # Cleaned warehouse-ready data
│       ├── src_college_placement.csv            # Placement dataset (10,000 rows)
│       ├── src_ds_student_marks.csv             # Data science course marks (497 rows)
│       ├── src_placement_prediction_2026.csv    # Placement prediction source (100,000 rows)
│       ├── src_skill_scores.csv                 # Skill evaluation scores (200 rows)
│       │
│       └── v5/                                  # Production Star-Schema Warehouse Tables
│           ├── dim_student.csv                  # Student dimension spine (1,200 × 6)
│           ├── fact_risk_behaviour.csv          # Risk & behavioral fact table (1,200 × 36)
│           ├── fact_placement.csv               # Placement facts & package predictions (1,200 × 21)
│           ├── fact_skill_scores.csv            # Technical & analytical skill scores (10,955 × 7)
│           ├── dim_cs_skills_v5.csv             # CS skills & profile reference (180 × 14)
│           ├── data_lineage_v5.md               # Column-level lineage documentation
│           ├── data_quality_report.md           # 25/25 QA validation checks passed
│           ├── null_handling_report.md          # Documented null handling strategies
│           └── removed_columns.md               # Audit of excluded columns
│
├── etl/                                         # ETL pipeline scripts
├── models/                                      # ML models & training pipelines
├── dashboard/                                   # Dashboard & visualization layer
├── genai/                                       # GenAI insights & recommendation layer
│
├── IMPLEMENTATION_PLAN.md                       # Full 7-phase platform architectural plan
├── requirements.txt                             # Python dependencies
└── README.md
```

---

## 🏛️ Warehouse Star Schema (v5)

| Table | Type | Rows | Columns | Primary Key / Keys | Description |
|---|---|---|---|---|---|
| `dim_student` | Dimension | 1,200 | 6 | `master_student_id` | Master student spine (MSTU00001–MSTU01200) with demographics & cohort |
| `fact_risk_behaviour` | Fact | 1,200 | 36 | `master_student_id` | Survey lifestyle, study habits, and `performance_risk_level` target |
| `fact_placement` | Fact | 1,200 | 21 | `master_student_id` | Placement status, salary package LPA, hackathons, and readiness scores |
| `fact_skill_scores` | Fact | 10,955 | 7 | (`master_student_id`, `skill`) | Long-format technical skills (Python, SQL, ML, Power BI, Excel, English) |
| `dim_cs_skills_v5` | Dimension | 180 | 14 | `cs_ref_id` | Reference CS profile, domain interests, and programming languages |

---

## ⚙️ Setup & Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 📋 Data Quality & Governance

- **Target Preservation:** Target label `performance_risk_level` is strictly preserved without imputation.
- **Scale Separation:** 4.0 GPA and 10.0 CGPA scales are maintained separately with clear scale notes.
- **Probabilistic Join Transparency:** Every synthetic match is explicitly flagged with `is_synthetic_*` columns.
- **Audit Reports:** Full data lineage, null handling justification, and QA checks are versioned in `data/processed/v5/`.
