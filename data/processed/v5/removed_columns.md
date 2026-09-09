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
| `src_uci_subject_marks.csv` | `school` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `sex` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `age` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `address` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `famsize` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `pstatus` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `medu` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `fedu` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `mjob` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `fjob` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `reason` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `guardian_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `traveltime_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `studytime_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `failures_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `schoolsup_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `famsup_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `paid_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `activities_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `nursery` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `higher_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `internet` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `romantic_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `famrel_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `freetime_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `goout_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `dalc_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `walc_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `health_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `absences_mat` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `guardian_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `traveltime_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `studytime_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `failures_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `schoolsup_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `famsup_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `paid_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `activities_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `higher_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `romantic_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `famrel_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `freetime_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `goout_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `dalc_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `walc_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `health_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_uci_subject_marks.csv` | `absences_por` | Lifestyle/demographic fields not melted into fact_subject_marks; retained in separate dim if needed. Excluded to keep fact_subject_marks lean. |
| `src_skill_scores.csv` | `Student Placed` | Placement outcome — authoritative source is src_placement_prediction_2026 via fact_placement |
| `src_ds_student_marks.csv` | `location` | City name — not analytic for academic performance; no join key |
| `src_ds_student_marks.csv` | `student_id` | Non-overlapping integer namespace from different source |