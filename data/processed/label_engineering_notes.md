# Label Engineering Notes: `at_risk_flag`

## 1. Problem Context & Target Invalidation
- **`anchor_placement_status` Invalidation:** Raw placement status exhibits extreme class imbalance (98.4% "Placed" vs 1.6% "Not Placed"). A model trained on this target achieves 98.4% dummy accuracy by predicting majority class on all instances, failing to provide actionable predictive utility.
- **`navin_placement_status` Invalidation:** The Navin Patidar source dataset records exclusively placed students (100% positive class, zero negative examples), making it mathematically impossible to train a binary classifier.

## 2. Engineered Composite Definition
To construct a robust institutional early warning signal across all 25,000 students, an academic and operational composite metric was engineered:

```python
at_risk_flag = 1 if (
    anchor_backlog_history >= 1
    OR anchor_attendance_percentage < 55
    OR anchor_cgpa < 5.5
) else 0
```

## 3. Threshold Calibration & Distribution Progression
1. **Baseline Evaluation:**
   - Condition: `(anchor_backlog_history >= 1) OR (anchor_attendance_percentage < 65) OR (anchor_cgpa < 6.0)`
   - Positive Class: **39.77%** (9,943 students)
   - Negative Class: **60.23%** (15,057 students)
   - Analysis: Because `anchor_backlog_history >= 1` alone accounts for 30.39% of the student population, combining with attendance < 65% and CGPA < 6.0 yields ~39.77% positive class, slightly exceeding the 35% ceiling.

2. **Locked Calibrated Thresholds:**
   - Condition: `(anchor_backlog_history >= 1) OR (anchor_attendance_percentage < 55) OR (anchor_cgpa < 5.5)`
   - Positive Class: **31.89%** (7,973 students)
   - Negative Class: **68.11%** (17,027 students)
   - Ratio: **68.1% / 31.9%**
   - Compliance: Meets the target window of **65/35 to 80/20** class balance (positive class between 20% and 35%).

## 4. Academic Rationale
- **Backlogs (`>= 1`):** Having an active or historical backlog represents a direct credit deficit requiring remediation before graduation.
- **Severe Attendance Deficit (`< 55%`):** Falls well below statutory UGC/AICTE minimum attendance thresholds (75%), triggering institutional examination debarment.
- **Critical Academic Risk (`< 5.5 CGPA`):** Places the student in the bottom ~1.5% percentile of institutional GPA, severely jeopardizing campus placement eligibility.
