# Campus360

Campus360 is a student analytics platform that brings academic, behavioral, attendance, and career data together to understand student performance, identify learning gaps, and support better academic and career decisions.

---

## 📁 Folder Structure

```
Campus360/
│
├── DATA SET/                                         # Raw source files (original, unmodified)
│   ├── career_path_in_all_field.csv                  # Career paths across all fields (9000 rows)
│   ├── cs_students.csv                               # CS student skills snapshot (180 rows)
│   ├── enhanced_student_habits_performance_dataset.csv  # Habits & performance (80000 rows)
│   ├── hybrid_student_performance_1200.csv           # Risk survey data (1200 rows)
│   ├── student-mat.csv                               # UCI Math grades (sep=';', 395 rows)
│   ├── student-por.csv                               # UCI Portuguese grades (sep=';', 649 rows)
│   ├── student_lifestyle_dataset.csv                 # Student lifestyle data (2000 rows)
│   ├── student-merge.R                               # Original R merge script (UCI reference)
│   └── student.txt                                   # UCI dataset description
│
├── data/
│   ├── raw/                                          # (reserved for future raw ETL intake)
│   └── processed/                                    # All cleaned & stitched output files
│       │
│       ├── career_path_in_all_field.csv              # Standardised (snake_case)
│       ├── cs_students.csv                           # Standardised (snake_case)
│       ├── enhanced_student_habits_performance_dataset.csv  # Standardised (snake_case)
│       ├── hybrid_student_performance_1200.csv       # Standardised (snake_case)
│       ├── hybrid_student_performance_1200_clean.csv # Nulls imputed (511 → 0)
│       ├── student-mat.csv                           # Standardised (snake_case, sep=';')
│       ├── student-por.csv                           # Standardised (snake_case, sep=';')
│       ├── student_lifestyle_dataset.csv             # Standardised (snake_case)
│       │
│       ├── subject_marks_linked.csv                  # Math + Portuguese merged on 13 keys (382 rows)
│       ├── student_spine.csv                         # 5000-row synthetic student base (STU00001–STU05000)
│       ├── student_spine_with_marks.csv              # Spine + GPA-band matched subject marks
│       ├── student_spine_with_career.csv             # Spine + career data attached
│       │
│       ├── fact_risk_training.csv                    # At-risk model training table (1200 rows)
│       ├── dim_cs_skills.csv                         # CS skills dimension table (180 rows)
│       │
│       ├── stitched_student_master.csv               # Final stitched master (5000 × 44)
│       └── stitched_student_master_v2.csv            # v2: capped reuse (max 18×) + jitter applied
│
├── etl/                                              # ETL pipeline scripts (upcoming)
├── models/                                           # ML model training & artifacts (upcoming)
├── dashboard/                                        # Streamlit dashboard (upcoming)
├── genai/                                            # GenAI layer / LLM integration (upcoming)
│
├── requirements.txt                                  # Python dependencies
└── venv/                                             # Python virtual environment (not tracked)
```

---

## 🗂️ Data Stitching Pipeline (Steps 1–9)

| Step | Output File | Description |
|------|-------------|-------------|
| 1 | `processed/*.csv` | Standardise all 7 source files to snake_case |
| 2 | `subject_marks_linked.csv` | Merge Math + Portuguese on 13 shared keys → 382 rows |
| 3 | `hybrid_student_performance_1200_clean.csv` | Impute 511 missing values (median / "Not specified") |
| 4 | `student_spine.csv` | Sample 5000 rows from habits dataset, assign STU IDs |
| 5 | `student_spine_with_marks.csv` | GPA-band match subject marks onto spine |
| 6 | `student_spine_with_career.csv` | Attach career data by field mapping |
| 7 | `fact_risk_training.csv`, `dim_cs_skills.csv` | Separate risk & CS-skills tables |
| 8 | Validation | 4/4 integrity checks passed |
| 9 | `stitched_student_master.csv` | Frozen master table, column-ordered |
| fix | `stitched_student_master_v2.csv` | Reuse capped at 18×, ±1 jitter applied |

---

## ⚙️ Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📦 Dependencies

```
pandas
numpy
scikit-learn
sqlalchemy
psycopg2-binary
streamlit
```
