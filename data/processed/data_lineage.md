# Data Lineage & Stitching Architecture Report
### Student Academic Success, Subject Performance & Career Readiness Analytics Platform
**Hackathon:** KENEXA AI Hackathon (Problem Code: KDAC-3)  
**Author / Team:** Om Patel & Rahil Nagariya (Team ID: 60)  
**Target Audience:** Hackathon Evaluation Jury, Academic Data Architects & Mentors

---

## 1. Executive Summary

In higher education institutions, student data is notoriously fragmented across disconnected silos:
- **ERP / Academic Registrars:** Subject exam marks, attendance records, and term pass/fail flags.
- **Placement & Corporate Relations Cells:** Off-campus/on-campus offers, company packages, internship history, and coding profiles.
- **Wellness & Student Affairs Offices:** Sleep patterns, stress levels, mental health indicators, and lifestyle surveys.

To build a **360° Student Intelligence Platform**, this pipeline stitches **6 independent real-world Indian student datasets** into a coherent data warehouse using **Attribute-Based Probabilistic Similarity Matching**. Rather than joining randomly or simulating ungrounded synthetic students, this methodology preserves true multivariate distributions, ensuring correlations between academic ability, lifestyle habits, and placement outcomes remain statistically realistic.

---

## 2. Ingested Datasets Overview

| Dataset Key | Canonical Filename | Source Author / Origin | Raw Rows | Clean Rows | Focus Area | Native Performance Metric |
|---|---|---|---|---|---|---|
| **shambhuraje** | `shambhuraje_placement_career_2026.csv` | Shambhuraje (2026) | 25,000 | 25,000 | **MASTER ANCHOR**: Academics, coding profiles, lifestyle habits, career placement | `cgpa` (5.0 – 10.0 scale) |
| **kundan** | `kundan_student_performance.csv` | Kundan (India) | 25,000 | 15,000 | Secondary academics, study method, school type, travel time | `overall_score` (0 – 100 scale) |
| **sakharebharat** | `sakharebharat_indian_placement_2025.csv` | Sakhare Bharat (2025) | 12,000 | 12,000 | Engineering placement, coding/communication skills, aptitude, packages | `cgpa` (5.5 – 9.8 scale) |
| **suvidya** | `suvidya_student_performance.csv` | Suvidya (India) | 5,000 | 5,000 | School/Intermediate marks (Math, Science, English), pass/fail | `final_percentage` (36% – 98%) |
| **sehaj** | `sehaj_student_lifestyle.csv` | Sehaj Sharma (Kaggle) | 2,000 | 2,000 | Student lifestyle, physical activity, sleep hours, stress | `gpa` (2.24 – 4.0 scale) |
| **navinpatidar** | `navinpatidar_indian_placement.csv` | Navin Patidar (India) | 1,000 | 1,000 | Campus placement, company, job role, package in INR | `salary_inr` (₹301k – ₹1,198k) |

---

## 3. Anchor Selection & Institutional Identity Spine

- **Anchor Dataset:** `shambhuraje_placement_career_2026.csv` was selected as the **Golden Record (Spine)** because:
  1. It is the largest single dataset (25,000 records).
  2. It contains the widest feature breadth (44 attributes covering academics, coding profiles, lifestyle wellness, AI-tool usage, and placement results).
  3. It spans realistic Indian collegiate demographics across diverse branches (Computer Science, AI & DS, IT, Electronics, Mechanical, Civil) and states.
- **Institutional Master ID (`student_id`):**
  Each row in the anchor dataset is assigned an immutable, standard primary key:  
  `STU00001` through `STU25000`. This key serves as the universal foreign key across all dimension and fact tables in the star schema.

---

## 4. Attribute-Based Matching Methodology

### Why Not Identity or Purely Random Joins?
- **Identity Joins Impossible:** None of the 6 datasets share a real student identifier (some have row counters `1..N`, others strings `S0001`).
- **Random Joins Destroy Meaning:** Random merging produces nonsensical personas (e.g. a student with a 9.5 CGPA in engineering having a 22% mark in school math, or a student sleeping 2 hours daily with zero stress and top-tier placement).

### The 2-Tier Attribute Banding Algorithm
For each of the 5 secondary datasets:
1. **Performance Banding:**
   Each dataset is partitioned into 3 equal tertiles based on its own native academic metric:
   - **High Band:** Top 33% (e.g., Anchor CGPA >= 8.0, Suvidya >= 75%, Kundan >= 70, Sehaj GPA >= 3.3).
   - **Medium Band:** Middle 33% (e.g., Anchor CGPA 6.5 – 8.0).
   - **Low Band:** Bottom 33% (e.g., Anchor CGPA < 6.5).
2. **Demographic & Branch Clustering:**
   - Branches are classified into standard institutional clusters:
     - `Tech`: Computer Science, IT, AI & DS, Software Engineering.
     - `Core_Engineering`: Mechanical, Electrical, Civil, Electronics.
     - `General`: Arts, Commerce, Management, Sciences.
   - Demographics matched on `Gender` (`Male`, `Female`, `Other`) where reported.
3. **Sampling Without Replacement:**
   - Within each `(Performance Band, Demographic Cluster)` bucket, records from the smaller dataset are randomly paired to anchor students without replacement (seeded with deterministic random states for 100% reproducibility).
   - If a source demographic sub-bucket overflows, remaining records are matched within the **exact same performance band**, guaranteeing that academic capability is strictly preserved.
   - **Constraint:** Every anchor student receives **at most one** record from each source dataset. Unmatched anchor students retain `NULL` for those source columns, accompanied by explicit boolean flags (`has_suvidya_match`, `has_kundan_match`, etc.).

### Empirical Validation: Correlation Preservation
Post-stitching statistical checks demonstrate that academic integrity is firmly maintained across sources:
- Anchor CGPA vs. Sakhare CGPA: **r = 0.842** (n = 12,000)
- Anchor CGPA vs. Kundan Overall Score: **r = 0.824** (n = 15,000)
- Anchor CGPA vs. Suvidya Final Percentage: **r = 0.807** (n = 5,000)
- Anchor CGPA vs. Sehaj GPA: **r = 0.805** (n = 2,000)
- Anchor CGPA vs. Navin Placement Salary: **r = 0.853** (n = 1,000)

---

## 5. Synthetic vs. Original Field Audit

| Table | Column Name | Origin Source | Type | Transformation / Description |
|---|---|---|---|---|
| **dim_student** | `student_id` | Pipeline generated | **Synthetic PK** | Format `STU00001` - `STU25000` |
| **dim_student** | `gender`, `age` | `shambhuraje` | **Original** | Standardized casing |
| **dim_student** | `stream_branch`, `degree` | `shambhuraje` | **Original** | Engineering branch and degree programme |
| **dim_student** | `college_tier`, `city_tier`, `state` | `shambhuraje` | **Original** | Institutional classification |
| **dim_student** | `family_income_lpa` | `shambhuraje` | **Original** | Annual family income in LPA |
| **fact_performance** | `subject` | `suvidya`, `kundan`, `shambhuraje` | **Transformed** | Melted long-format subject name (Math, Science, English, Degree CGPA) |
| **fact_performance** | `marks` | `suvidya`, `kundan`, `shambhuraje` | **Original** | Exam score on respective subject scale |
| **fact_performance** | `max_marks` | System metadata | **Derived** | Assessment scale denominator (100.0 for school/term, 10.0 for CGPA) |
| **fact_performance** | `attendance_pct` | `suvidya`, `kundan`, `shambhuraje` | **Original** | Clipped to valid range [0.0, 100.0] |
| **fact_lifestyle** | `sleep_hours` | `shambhuraje` | **Original** | Imputed median on 500 missing values, clipped |
| **fact_lifestyle** | `screen_time_hours`, `gaming_hours` | `shambhuraje` | **Original** | Daily hours recorded in survey |
| **fact_lifestyle** | `stress_level`, `burnout_score` | `shambhuraje` | **Original** | Normalized 0-100 wellness index |
| **fact_lifestyle** | `physical_activity_hours_sehaj` | `sehaj` | **Original** | Hours per day from matched Sehaj survey |
| **fact_lifestyle** | `lifestyle_risk_flag` | Pipeline rule engine | **Derived** | `High Risk` if sleep < 5h or stress > 75 or burnout > 75; else `Normal` |
| **fact_career** | `cgpa`, `backlogs` | `shambhuraje` | **Original** | Academic career prerequisites |
| **fact_career** | `internships`, `dsa_problems_solved` | `shambhuraje` | **Original** | Technical preparation milestones |
| **fact_career** | `coding_skills_sakhare` | `sakharebharat` | **Original** | 1-10 skill rating from matched 2025 placement survey |
| **fact_career** | `salary_lpa` | `shambhuraje` | **Original** | Annual package offered (LPA) |
| **fact_career** | `placement_status`, `company_type` | `shambhuraje` | **Original** | Employment result and organization profile |
| **fact_career** | `layoffs_risk_score` | `shambhuraje` | **Original** | Predictive risk indicator for career coaching |

---

## 6. Key Data Engineering Assumptions

1. **Deduplication:**
   `kundan_student_performance.csv` contained 10,000 exact duplicates in its raw download. These were safely pruned in `clean.py` down to the 15,000 unique records described in the project blueprint.
2. **Missingness Preservation:**
   Because anchor students outnumber secondary datasets (e.g. 1,000 Navinpatidar rows vs 25,000 anchor students), we deliberately do **not** hallucinate synthetic records to fill remaining slots. Unmatched rows naturally have `NULL` values and are tracked with `has_*_match` indicator flags, maintaining scientific honesty.
3. **Scale Coexistence:**
   GPA on the 4.0 scale (`sehaj`) and CGPA on the 10.0 scale (`sakhare`, `shambhuraje`) are retained on their native scales in their respective source columns and clearly labeled with `max_marks` metadata in `fact_performance.csv` to avoid scale confusion.
4. **Reproducibility:**
   All stochastic matching steps use fixed random seeds (`random_state = 42, 101, 202, 303, 404`). Re-running the pipeline yields bit-for-bit identical tables every time.
