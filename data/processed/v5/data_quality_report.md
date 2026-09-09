# Data Quality Report — v5 Star Schema

## Before Processing

| Source | Rows | Cols | Duplicate Rows | Total Nulls |
|---|---|---|---|---|
| `spine` | 1,200 | 36 | 0 | 511 |
| `cs_raw` | 180 | 12 | 0 | 0 |
| `uci` | 382 | 54 | 0 | 0 |
| `placement` | 100,000 | 26 | 0 | 0 |
| `skill_scores` | 200 | 6 | 0 | 0 |
| `ds_marks` | 497 | 8 | 0 | 0 |
| `college` | 10,000 | 10 | 0 | 0 |

## After Processing

| Output Table | Rows | Cols | Total Nulls | High-Null Columns |
|---|---|---|---|---|
| `dim_student.csv` | 1,200 | 6 | 0 | none |
| `fact_risk_behaviour.csv` | 1,200 | 36 | 0 | none |
| `fact_placement.csv` | 1,200 | 21 | 0 | none |
| `fact_subject_marks.csv` | 2,292 | 10 | 2292 | master_student_id(2292) |
| `fact_skill_scores.csv` | 10,955 | 7 | 0 | none |
| `dim_cs_skills_v5.csv` | 180 | 14 | 0 | none |

## Range Issues Detected

| Table | Column | Issue | Count |
|---|---|---|---|
| — | — | No range issues detected | — |

## Quality Checks Summary

| Check | Status | Detail |
|---|---|---|
| dim_student row count = 1,200 | ✅ PASS | actual=1200 |
| fact_risk_behaviour row count = 1,200 | ✅ PASS | actual=1200 |
| fact_placement row count = 1,200 | ✅ PASS | actual=1200 |
| fact_subject_marks row count = 2,292 (382×2×3) | ✅ PASS | actual=2292, expected=2292 |
| dim_cs_skills_v5 row count = 180 | ✅ PASS | actual=180 |
| dim_student: master_student_id unique | ✅ PASS |  |
| fact_risk_behaviour: master_student_id unique | ✅ PASS |  |
| fact_placement: master_student_id unique | ✅ PASS |  |
| dim_cs_skills_v5: cs_ref_id unique | ✅ PASS |  |
| master_student_id namespace safe (no STU collision) | ✅ PASS |  |
| fact_risk_behaviour FK → dim_student valid | ✅ PASS |  |
| fact_placement FK → dim_student valid | ✅ PASS |  |
| fact_skill_scores FK → dim_student valid (non-null) | ✅ PASS |  |
| performance_risk_level (target) not imputed | ✅ PASS | 0 nulls preserved intentionally |
| dim_student: no duplicate rows | ✅ PASS |  |
| fact_risk_behaviour: no duplicate rows | ✅ PASS |  |
| fact_placement: no duplicate rows | ✅ PASS |  |
| salary_package_lpa >= 0 | ✅ PASS | 0 negatives |
| skill_scores (0-1 scale) in range | ✅ PASS | 0 out of range |
| ds_marks (0-100 scale) in range | ✅ PASS | 0 out of range |
| fact_placement: no near-duplicate numeric columns (corr≥0.95) | ✅ PASS | 0 pairs |
| fact_placement: is_synthetic_placement_match=True for all rows | ✅ PASS |  |
| fact_skill_scores: is_synthetic_match=True for all rows | ✅ PASS |  |
| fact_subject_marks: is_synthetic=False for all UCI rows (real data) | ✅ PASS |  |
| dim_student: no banned v3 columns | ✅ PASS |  |
| fact_risk_behaviour: no banned v3 columns | ✅ PASS |  |
| fact_placement: no banned v3 columns | ✅ PASS |  |