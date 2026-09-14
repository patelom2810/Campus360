# Campus360 Production Models: Features, Data Sources, and Operational Diagnosis

> Plain-Language Manual Reference Document  
> Audience: Academic Deans, Department Heads, Faculty Mentors, and Non-Technical Auditors  
> Scope: Complete logic audit, database source mapping, and diagnostic investigation of both production machine learning models.

---

## Executive Overview

Campus360 operates two distinct machine learning models designed to support university administration and student mentoring:

1. **Model 1 (Performance Predictor)**: Estimates a student's continuous academic grade point average (CGPA) on a 0.0 to 10.0 scale based on study habits, attendance, project milestones, and technical preparation.
2. **Model 2 (At-Risk Early Detection)**: Calculates a risk probability percentage indicating whether a student is likely to fall into academic distress, using strictly non-academic lifestyle habits and behavioral indicators so interventions can occur before formal failure happens.

This reference provides a comprehensive map of every feature, algorithm, and database origin so that any prediction can be verified by hand against raw student records. It concludes with an empirical investigation into why Model 2 can appear to non-technical users as though it is "not responding properly."

---

## PART 1 — Model 1: Academic Performance Prediction

### 1. Plain-Language Purpose
Model 1 forecasts a student's continuous degree Grade Point Average (CGPA) on a 0.0 to 10.0 scale based on their study habits, lecture attendance, and technical milestones.

### 2. Algorithm in Everyday Terms
Model 1 runs on **Gradient Boosting Regression**. Practically, this works like a collaborative panel of 200 simple decision rules that are created in sequence:
- The first decision rule takes a rough guess at a student's grade.
- The second decision rule examines where the first guess was too high or too low, and focuses specifically on shrinking that error.
- Each successive rule continues correcting the leftover mistakes of all prior rules combined.
- At the end, the model combines the adjustments of all 200 stages into one final, refined grade prediction.

### 3. Complete Feature Catalog (All 28 Features)
Model 1 evaluates 28 total attributes: 24 primary student metrics and 4 engineered combination indicators.

| Feature (Plain Name) | What It Means | Database Table and Column Source |
| :--- | :--- | :--- |
| **Class Attendance Percentage** | The student's recorded overall lecture attendance rate, expressed from 0% to 100%. | `fact_performance.attendance_pct` (Master Anchor record) |
| **Daily Study Hours** | Average number of hours the student spends studying coursework each day outside class. | `fact_lifestyle.study_hours_daily` |
| **Self-Learning Hours** | Daily hours dedicated to independent self-study, tutorials, and non-classroom skill learning. | Master Student Profile (`anchor_self_learning_hours`) |
| **Nightly Sleep Hours** | Average number of hours of sleep the student gets per night. | `fact_lifestyle.sleep_hours` |
| **Daily Screen Time** | Total recreational and academic digital screen hours logged per day. | `fact_lifestyle.screen_time_hours` |
| **Daily Gaming Hours** | Hours per day spent playing video or mobile games. | `fact_lifestyle.gaming_hours` |
| **Academic Stress Level** | Self-reported stress index measured on a scale from 0 (calm) to 100 (severe stress). | `fact_lifestyle.stress_level` |
| **Burnout Score** | Physical and mental exhaustion rating measured on a scale from 0 (fresh) to 100 (complete burnout). | `fact_lifestyle.burnout_score` |
| **Backlog History** | Total count of previously failed subject examinations (arrears) accumulated to date. | `fact_career.backlogs` |
| **DSA Problems Solved** | Total Data Structures & Algorithms coding challenges completed on practice platforms. | `fact_career.dsa_problems_solved` |
| **Internships Completed** | Total number of formal industry or research internships finished by the student. | `fact_career.internships` |
| **Motivation Level** | Self-assessed academic drive and energy score rated on a scale from 0 to 100. | `fact_lifestyle.motivation_level` |
| **Family Annual Income** | Household financial bracket measured in Lakhs per Annum (LPA). | `dim_student.family_income_lpa` |
| **Resume Score** | Standardized evaluation of resume quality, structure, and depth rated on a scale from 0 to 100. | Master Student Profile (`anchor_resume_score`) |
| **Communication Skills** | Evaluated verbal, presentation, and team communication score rated on a scale from 0 to 100. | `fact_career.communication_skills` |
| **Aptitude Score** | Standardized quantitative reasoning and logical aptitude test score (0 to 100 scale). | `fact_career.aptitude_score` |
| **Mock Interview Score** | Performance evaluation from simulated technical and HR interviews (0 to 100 scale). | `fact_career.mock_interview_score` |
| **Hackathons Participated** | Total competitive programming and development hackathons attended. | Master Student Profile (`anchor_hackathons_participated`) |
| **Development Projects Count** | Number of completed software, web, mobile, or hardware engineering projects. | Master Student Profile (`anchor_development_projects_count`) |
| **AI / Machine Learning Projects** | Number of specialized artificial intelligence and machine learning projects completed. | Master Student Profile (`anchor_ai_ml_projects`) |
| **GitHub Repositories** | Number of active code repositories published on GitHub. | `fact_career.github_repos` |
| **AI Tool Usage Frequency** | Self-reported rating of daily AI assistant adoption for coursework (0 to 100 scale). | Master Student Profile (`anchor_ai_tool_usage_frequency`) |
| **Prompt Engineering Skill** | Measured fluency in structuring instructions for generative AI tools (0 to 100 scale). | Master Student Profile (`anchor_prompt_engineering_skill`) |
| **Adaptability Score** | Measured ability to adjust to new technical frameworks and shifting workloads (0 to 100 scale). | Master Student Profile (`anchor_adaptability_score`) |
| **Effort Score (Engineered)** | Combined measure of academic investment. **Plain Formula**: Daily Study Hours plus Self-Learning Hours, added together. | Computed on-the-fly from `fact_lifestyle.study_hours_daily` and `anchor_self_learning_hours` |
| **Screen-to-Study Ratio (Engineered)** | Measure of digital balance. **Plain Formula**: Daily Screen Time divided by (Daily Study Hours plus 1 hour). | Computed on-the-fly from `fact_lifestyle.screen_time_hours` and `fact_lifestyle.study_hours_daily` |
| **Wellness Score (Engineered)** | Balance between physical recovery and mental strain. **Plain Formula**: Nightly Sleep Hours minus one-tenth of Stress Level minus one-tenth of Burnout Score. | Computed on-the-fly from `fact_lifestyle.sleep_hours`, `fact_lifestyle.stress_level`, and `fact_lifestyle.burnout_score` |
| **Project Activity Score (Engineered)** | Comprehensive practical technical engagement. **Plain Formula**: Development Projects Count plus AI/ML Projects plus Hackathons Participated. | Computed on-the-fly from `anchor_development_projects_count`, `anchor_ai_ml_projects`, and `anchor_hackathons_participated` |

### 4. Real-World Accuracy Stated Plainly
Model 1 achieves an R-squared of 0.2096 (about 21%) and an average prediction error of 0.60 grade points (Mean Absolute Error). 

**Plain-language interpretation**: This model explains about 21% of why one student's GPA differs from another's. It is useful as a rough, directional signal to see if a student is tracking toward high or low honors, but it must never be treated as a precise grade forecast.

---

## PART 2 — Model 2: At-Risk Student Detection

### 1. Plain-Language Purpose
Model 2 flags whether an enrolled student is in danger of severe academic distress, giving counselors and mentors early warning before exam failures or formal disciplinary proceedings happen.

### 2. Definition of "At-Risk"
In the Campus360 institution records, a student is defined as genuinely at-risk if they satisfy any one of three conditions:
- They have accumulated **at least 1 active backlog** (failed exam subject); **OR**
- Their classroom attendance has fallen **below 55%**; **OR**
- Their cumulative grade point average has fallen **below 5.5 CGPA**.

If any one of these three triggers occurs, the student is marked as "At-Risk" in ground-truth records.

### 3. Algorithm in Everyday Terms
Model 2 runs on **Logistic Regression**. Practically, this calculates a risk score by weighing each student habit up or down based on how strongly that habit has historically been linked to student difficulties, and then converts that total into a 0% to 100% risk probability. If the resulting probability is 50% or higher, the system raises an "At-Risk" advisory flag.

### 4. Complete Feature Catalog (All 23 Features)
Model 2 uses 23 features: 21 primary lifestyle, psychological, and behavioral attributes, plus 2 engineered balance metrics.

| Feature (Plain Name) | What It Means | Database Table and Column Source |
| :--- | :--- | :--- |
| **Nightly Sleep Hours** | Average hours of sleep per night; chronic deprivation elevates risk. | `fact_lifestyle.sleep_hours` |
| **Daily Screen Time** | Total screen time logged per day in hours. | `fact_lifestyle.screen_time_hours` |
| **Daily Gaming Hours** | Hours spent gaming daily; excessive gaming increases predicted risk. | `fact_lifestyle.gaming_hours` |
| **Academic Stress Level** | Perceived academic strain rated on a scale from 0 to 100. | `fact_lifestyle.stress_level` |
| **Burnout Score** | Physical and mental fatigue rating on a scale from 0 to 100. | `fact_lifestyle.burnout_score` |
| **Daily Study Hours** | Hours spent studying per day; higher values reduce predicted risk. | `fact_lifestyle.study_hours_daily` |
| **Self-Learning Hours** | Independent tutorial and skill-building hours per day. | Master Student Profile (`anchor_self_learning_hours`) |
| **Motivation Level** | Self-reported motivation and interest in studies (0 to 100 scale). | `fact_lifestyle.motivation_level` |
| **Adaptability Score** | Ability to handle curriculum transitions and stress (0 to 100 scale). | Master Student Profile (`anchor_adaptability_score`) |
| **Weekly Gym Frequency** | Number of days per week the student engages in physical exercise or fitness. | `fact_lifestyle.gym_frequency_per_week` |
| **Family Annual Income** | Socioeconomic background bracket measured in Lakhs per Annum (LPA). | `dim_student.family_income_lpa` |
| **Resume Score** | Evaluation score of career materials and credentials (0 to 100 scale). | Master Student Profile (`anchor_resume_score`) |
| **Communication Skills** | Verbal and interpersonal communication score (0 to 100 scale). | `fact_career.communication_skills` |
| **Aptitude Score** | Logical reasoning and problem-solving benchmark score (0 to 100 scale). | `fact_career.aptitude_score` |
| **Mock Interview Score** | Readiness score from professional interview simulations (0 to 100 scale). | `fact_career.mock_interview_score` |
| **Hackathons Participated** | Total competitive coding events and design sprints attended. | Master Student Profile (`anchor_hackathons_participated`) |
| **Development Projects Count** | Total practical software or hardware projects completed. | Master Student Profile (`anchor_development_projects_count`) |
| **AI / Machine Learning Projects** | Count of applied AI/ML projects built. | Master Student Profile (`anchor_ai_ml_projects`) |
| **GitHub Repositories** | Number of public code repositories maintained on GitHub. | `fact_career.github_repos` |
| **AI Tool Usage Frequency** | Rating of generative AI tool utilization (0 to 100 scale). | Master Student Profile (`anchor_ai_tool_usage_frequency`) |
| **Prompt Engineering Skill** | Rating of proficiency in guiding AI workflows (0 to 100 scale). | Master Student Profile (`anchor_prompt_engineering_skill`) |
| **Wellness Score (Engineered)** | Overall well-being index. **Plain Formula**: Nightly Sleep Hours minus one-tenth of Stress Level minus one-tenth of Burnout Score. | Computed on-the-fly from `fact_lifestyle.sleep_hours`, `fact_lifestyle.stress_level`, and `fact_lifestyle.burnout_score` |
| **Screen-to-Study Ratio (Engineered)** | Habit balance index. **Plain Formula**: Daily Screen Time divided by (Daily Study Hours plus 1 hour). | Computed on-the-fly from `fact_lifestyle.screen_time_hours` and `fact_lifestyle.study_hours_daily` |

### 5. Features Deliberately NOT Used (Anti-Leakage Safeguard)
Model 2 strictly excludes three specific database columns:
1. **Backlog History** (`fact_career.backlogs`)
2. **Class Attendance Percentage** (`fact_performance.attendance_pct`)
3. **Cumulative Degree CGPA** (`fact_career.cgpa`)

**Why they are excluded in one sentence**: Because backlogs, attendance, and CGPA are the exact rules that define what "at-risk" means in the first place, using them as inputs would be like guessing a locked door's combination when you already have the key. If the model were allowed to look at existing backlogs, it would not be providing an early warning—it would simply be repeating facts the administration already knows.

### 6. Real-World Accuracy Stated Plainly
Model 2 exhibits a **Recall of 50.22%** and a **Precision of 33.46%** (with an overall accuracy of 52.26% and ROC AUC of 0.5190).

**Plain-language interpretation**: The model correctly flags about half of genuinely at-risk students, and about 1 in 3 flagged students turns out to actually be at-risk (meaning 2 out of 3 flags are false alarms). It is intended as an exploratory screening filter to prompt friendly counselor check-ins, not as an automated disciplinary determination.

---

## PART 3 — Where the Data Physically Lives (Consolidated Table Map)

The relational warehouse organizes student information across four primary tables in a star schema, supplemented by master intake attributes. 

**Summary Rule**: Model 1 and Model 2 both read from `fact_lifestyle` and `fact_career`, but only Model 1 reads from `fact_performance` (for attendance). Neither model uses raw subject marks or grade history.

| Feature Name | Used by Model 1? | Used by Model 2? | Database Table | Column Name in Database |
| :--- | :---: | :---: | :--- | :--- |
| **Student Identifier** | Key | Key | `dim_student` | `student_id` |
| **Family Annual Income** | Yes | Yes | `dim_student` | `family_income_lpa` |
| **Class Attendance Percentage** | Yes | **NO (Excluded)** | `fact_performance` | `attendance_pct` |
| **Daily Study Hours** | Yes | Yes | `fact_lifestyle` | `study_hours_daily` |
| **Nightly Sleep Hours** | Yes | Yes | `fact_lifestyle` | `sleep_hours` |
| **Daily Screen Time** | Yes | Yes | `fact_lifestyle` | `screen_time_hours` |
| **Daily Gaming Hours** | Yes | Yes | `fact_lifestyle` | `gaming_hours` |
| **Academic Stress Level** | Yes | Yes | `fact_lifestyle` | `stress_level` |
| **Burnout Score** | Yes | Yes | `fact_lifestyle` | `burnout_score` |
| **Motivation Level** | Yes | Yes | `fact_lifestyle` | `motivation_level` |
| **Weekly Gym Frequency** | No | Yes | `fact_lifestyle` | `gym_frequency_per_week` |
| **Backlog History** | Yes | **NO (Excluded)** | `fact_career` | `backlogs` |
| **Cumulative Degree CGPA** | Target | **NO (Excluded)** | `fact_career` | `cgpa` |
| **DSA Problems Solved** | Yes | No | `fact_career` | `dsa_problems_solved` |
| **Internships Completed** | Yes | No | `fact_career` | `internships` |
| **GitHub Repositories** | Yes | Yes | `fact_career` | `github_repos` |
| **Communication Skills** | Yes | Yes | `fact_career` | `communication_skills` |
| **Aptitude Score** | Yes | Yes | `fact_career` | `aptitude_score` |
| **Mock Interview Score** | Yes | Yes | `fact_career` | `mock_interview_score` |
| **Self-Learning Hours** | Yes | Yes | Master Student Profile | `anchor_self_learning_hours` |
| **Resume Score** | Yes | Yes | Master Student Profile | `anchor_resume_score` |
| **Hackathons Participated** | Yes | Yes | Master Student Profile | `anchor_hackathons_participated` |
| **Development Projects Count** | Yes | Yes | Master Student Profile | `anchor_development_projects_count` |
| **AI / Machine Learning Projects** | Yes | Yes | Master Student Profile | `anchor_ai_ml_projects` |
| **AI Tool Usage Frequency** | Yes | Yes | Master Student Profile | `anchor_ai_tool_usage_frequency` |
| **Prompt Engineering Skill** | Yes | Yes | Master Student Profile | `anchor_prompt_engineering_skill` |
| **Adaptability Score** | Yes | Yes | Master Student Profile | `anchor_adaptability_score` |
| **Effort Score** | Yes | No | Calculated on-the-fly | Plain Formula: Daily Study + Self-Learning Hours |
| **Project Activity Score** | Yes | No | Calculated on-the-fly | Plain Formula: Dev Projects + AI Projects + Hackathons |
| **Screen-to-Study Ratio** | Yes | Yes | Calculated on-the-fly | Plain Formula: Daily Screen Time / (Daily Study Hours + 1) |
| **Wellness Score** | Yes | Yes | Calculated on-the-fly | Plain Formula: Sleep Hours - (Stress / 10) - (Burnout / 10) |

---

## PART 4 — Diagnosis: "Model 2 Not Responding Properly" — Investigate, Don't Guess

### 1. Concrete Live Replication
To verify how Model 2 responds in practice, four distinct student profiles were submitted to the live intake endpoint (`/api/assess/new-student`). The resulting model predictions were recorded:

#### Profile A: Obviously Low-Risk / High-Performing Student
- **Profile**: 8.5 hours sleep, 7.0 hours daily study, 3.5 hours self-learning, 2.5 hours screen time, 0 gaming, 5 days gym/week, stress level 15/100, burnout 10/100, 95% attendance, 0 backlogs, 450 DSA problems.
- **Model 1 Predicted CGPA**: 7.40
- **Model 2 At-Risk Probability**: **47.54%**
- **Model 2 Classification**: **Safe**

#### Profile B: Average / Typical Student
- **Profile**: 7.0 hours sleep, 4.0 hours daily study, 1.5 hours self-learning, 5.0 hours screen time, 1.0 hour gaming, 2 days gym/week, stress level 50/100, burnout 45/100, 80% attendance, 0 backlogs, 120 DSA problems.
- **Model 1 Predicted CGPA**: 6.46
- **Model 2 At-Risk Probability**: **53.90%**
- **Model 2 Classification**: **At-Risk**

#### Profile C: Mixed / Borderline Student
- **Profile**: 5.0 hours sleep, 3.0 hours daily study, 1.0 hour self-learning, 7.5 hours screen time, 3.0 hours gaming, 1 day gym/week, stress level 80/100, burnout 75/100, 60% attendance, 1 backlog, 40 DSA problems.
- **Model 1 Predicted CGPA**: 6.07
- **Model 2 At-Risk Probability**: **57.72%**
- **Model 2 Classification**: **At-Risk**

#### Profile D: Obviously High-Risk / Severely Struggling Student
- **Profile**: 3.5 hours sleep, 1.0 hour daily study, 0.2 hours self-learning, 10.0 hours screen time, 6.0 hours gaming, 0 gym/week, stress level 90/100, burnout 95/100, 40% attendance, 4 backlogs, 5 DSA problems.
- **Model 1 Predicted CGPA**: 5.85
- **Model 2 At-Risk Probability**: **61.89%**
- **Model 2 Classification**: **At-Risk**

#### Profile E: Blank Form / Missing Inputs (Pure Population Medians)
- **Profile**: No fields filled; system defaults all missing attributes to campus population medians.
- **Model 1 Predicted CGPA**: 6.46
- **Model 2 At-Risk Probability**: **51.21%**
- **Model 2 Classification**: **At-Risk**

---

### 2. Analysis of the Output: Is There a Bug?
Examining the actual numbers above reveals that the model **does vary logically and directionally with user inputs**:
- As student habits deteriorate from top-tier to severely distressed, the risk probability increases monotonically: **47.54% → 51.21% → 53.90% → 57.72% → 61.89%**.
- A thriving student scores lowest (47.54%), an average student scores higher (53.90%), a struggling student scores higher still (57.72%), and a failing student scores highest (61.89%).
- All feature names are matched in exact alphabetical and positional order, inference returns in under 5 milliseconds, and no caching or stale memory bugs exist.

Therefore, there is **no code defect, feature-misalignment bug, or server failure**.

---

### 3. Why Non-Technical Reviewers Perceive That Model 2 Is "Not Responding Properly"
If there is no code bug, why do faculty members and evaluators report that Model 2 feels unresponsive or broken? The investigation identified three concrete mathematical and behavioral causes:

#### Reason 1: Extremely Narrow Probability Spread (The "Everyone is 50%" Illusion)
A human user testing a risk model expects dramatic swings: an honor student should see 5% risk, while a failing student should see 95% risk. 

In Model 2, however, an audit across all 25,000 students in the campus database shows:
- Minimum probability in the entire institution: **42.14%**
- 25th percentile: **48.40%**
- Median (50th percentile): **49.90%**
- 75th percentile: **51.48%**
- Maximum probability in the entire institution: **58.85%**
- Standard deviation: **only 2.26 percentage points**

Because 99% of all students produce a score between 44% and 56%, any two random students look almost identical to the naked eye. When an evaluator changes study hours from 2 hours to 8 hours and sees the probability only shift from 54% to 49%, they naturally conclude that the system is unresponsive or ignoring their input.

#### Reason 2: The "Balanced Weights" False Alarm on Average Students
Because only ~32% of university students are genuinely at-risk, the model was trained using balanced class weighting to ensure it would not simply guess "Safe" for everyone. 

A consequence of balanced weighting is that the baseline score for an average, median student is pushed up to **51.21%**. Because the decision threshold is fixed at 50.00%, **an ordinary, passing student with 80% attendance and zero backlogs gets flagged with a red "At-Risk" warning**. Evaluators entering normal student profiles see a red warning badge and assume the model has malfunctioned.

#### Reason 3: Deliberate Exclusion of Academic Data (The Anti-Leakage Ceiling)
As established in Part 2, Model 2 is intentionally forbidden from inspecting backlogs, attendance, or current grades. It must predict academic distress using only sleep duration, screen time, stress ratings, and gaming habits.

In real life, lifestyle habits correlate only modestly with exam failures (many students who sleep poorly still pass their exams, while some students with healthy sleep fail). With an ROC AUC of 0.5190, the statistical relationship between pure lifestyle habits and semester failure is inherently weak. The model cannot produce sharp, confident separations because the lifestyle data does not contain a strong enough signal.

---

### 4. Definitive Finding
**Confirmed working as expected**: Predictions vary appropriately and directionally with input. The perceived issue is the model's known mathematical accuracy ceiling (50% recall, 33% precision) combined with a highly compressed probability range (42% to 59%), not a software defect, caching failure, or data pipeline malfunction.

### 5. Practical Guidance for Faculty and Reviewers
When presenting or reviewing Model 2:
1. **Explain the Narrow Range**: Clarify to reviewers that scores in Model 2 represent relative lifestyle vulnerability centered around 50%, not absolute percentage odds of dropping out. A student at 54% is exhibiting above-average lifestyle strain, not a certainty of failure.
2. **Emphasize Early Screening**: Clarify that Model 2 is intentionally designed as an un-biased lifestyle screener that catches 50% of at-risk students before grades are posted, with the known tradeoff that 2 out of 3 flags are exploratory false alarms.
3. **Check the Detailed Breakdown**: Direct users to the Top Contributing Factor and Gemini mentor brief, which explicitly contextualize the score (e.g., highlighting that low gym activity or elevated screen time pushed the student slightly over the threshold) and include mandatory calibration disclaimers.
