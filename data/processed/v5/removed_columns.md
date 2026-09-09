# Removed Columns Report — v5

| Source File | Column | Reason |
|---|---|---|
| `hybrid_student_performance_1200.csv` | `timestamp` | Operational field — survey submission timestamp, not analytic |
| `cs_students.csv` | `student_name` | PII — student names dropped for privacy; src_cs_student_id retained for lineage |
| `src_placement_prediction_2026.csv` | `student_id` | Integer ID from different source — no overlap with spine IDs |
| `src_placement_prediction_2026.csv` | `age` | Already in dim_student from spine |
| `src_placement_prediction_2026.csv` | `gender` | Already in dim_student from spine |
| `src_placement_prediction_2026.csv` | `sleep_hours` | Already in fact_risk_behaviour from spine |
| `src_placement_prediction_2026.csv` | `study_hours_per_day` | study_hours_daily exists in fact_risk_behaviour from spine |
| `src_placement_prediction_2026.csv` | `attendance_percentage` | attendance_band exists in fact_risk_behaviour; different formats |
| `src_placement_prediction_2026.csv` | `cgpa` | Used only as matching key; spine uses cgpa_category band |
| `src_placement_prediction_2026.csv` | `branch` | Used only as matching key |
| `src_skill_scores.csv` | `Student Placed` | Placement outcome — authoritative source is src_placement_prediction_2026 via fact_placement |
| `src_ds_student_marks.csv` | `location` | City name — not analytic for academic performance; no join key |
| `src_ds_student_marks.csv` | `student_id` | Non-overlapping integer namespace from different source |