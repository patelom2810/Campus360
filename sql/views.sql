-- =============================================================================
-- Campus360 Analytical Views (SQLite Compatible)
-- Designed for Dashboards, Model Feature Engineering & Faculty 360 Profiling
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. STUDENT 360 HOLISTIC VIEW
-- Denormalized master view combining all 7 warehouse domains per student
-- -----------------------------------------------------------------------------
CREATE VIEW student_360_view AS
SELECT
    -- Core Student Demographics
    s.student_id,
    s.enrollment_date,
    s.family_income_lpa,
    s.cgpa,
    s.backlogs,
    s.backlogs AS backlog_history,
    s.failed_subjects,
    s.at_risk_flag,

    -- Academic Profile
    ar.previous_cgpa,
    ar.previous_semester_percentage,
    ar.previous_subject_avg,
    ar.weak_subject_count,
    ar.subject_consistency,
    ar.performance_band,

    -- Exam Component Marks & Future Target
    em.previous_internal_marks,
    em.previous_assignment_score,
    em.previous_midterm_score,
    em.lowest_subject_score,
    em.assignment_completion_rate,
    em.practice_questions,
    em.next_semester_marks,

    -- Engagement & Attendance
    att.attendance_percentage,
    att.study_hours_daily,
    att.self_learning_hours,
    att.study_hours_per_week,
    att.last_sync_time,

    -- Lifestyle & Mental Wellness
    lf.sleep_hours,
    lf.screen_time,
    lf.gaming_hours,
    lf.stress_level,
    lf.burnout_score,
    lf.motivation_level,
    lf.adaptability_score,
    lf.gym_frequency,
    lf.wellness_score,
    lf.screen_to_study_ratio,
    lf.extracurricular_hours,
    lf.survey_date,

    -- Placement & Technical Capabilities
    sk.resume_score,
    sk.communication_skills,
    sk.aptitude_score,
    sk.mock_interview_score,
    sk.development_projects_count,
    sk.ai_ml_projects,
    sk.git_hub_repos,
    sk.ai_tool_usage_frequency,
    sk.prompt_engineering_skill,

    -- Career Preferences
    cp.hackathons_participated,
    cp.preferred_domain,
    cp.career_goal,
    cp.submitted_at
FROM students s
LEFT JOIN academic_records ar ON s.student_id = ar.student_id
LEFT JOIN exam_marks em ON s.student_id = em.student_id
LEFT JOIN attendance att ON s.student_id = att.student_id
LEFT JOIN lifestyle lf ON s.student_id = lf.student_id
LEFT JOIN skills sk ON s.student_id = sk.student_id
LEFT JOIN career_preferences cp ON s.student_id = cp.student_id;

-- -----------------------------------------------------------------------------
-- 2. PERFORMANCE FEATURES VIEW (For Model 1: Regression)
-- -----------------------------------------------------------------------------
CREATE VIEW performance_features_view AS
SELECT
    s.student_id,
    s.cgpa,
    s.backlogs,
    s.failed_subjects,
    s.family_income_lpa,

    -- Academic history
    ar.previous_cgpa,
    ar.previous_semester_percentage,
    ar.previous_subject_avg,
    ar.weak_subject_count,
    ar.subject_consistency,

    -- Exam components
    em.previous_internal_marks,
    em.previous_assignment_score,
    em.previous_midterm_score,
    em.lowest_subject_score,
    em.assignment_completion_rate,
    em.practice_questions,

    -- Attendance & study
    att.attendance_percentage,
    att.study_hours_daily,
    att.self_learning_hours,
    att.study_hours_per_week,

    -- Lifestyle & stress
    lf.sleep_hours,
    lf.screen_time,
    lf.gaming_hours,
    lf.stress_level,
    lf.burnout_score,
    lf.motivation_level,
    lf.adaptability_score,
    lf.wellness_score,
    lf.screen_to_study_ratio,
    lf.extracurricular_hours,

    -- Target variable
    em.next_semester_marks AS target_next_semester_marks
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
JOIN exam_marks em ON s.student_id = em.student_id
JOIN attendance att ON s.student_id = att.student_id
JOIN lifestyle lf ON s.student_id = lf.student_id;

-- -----------------------------------------------------------------------------
-- 3. AT-RISK FEATURES VIEW (For Model 2: Screening Classification)
-- -----------------------------------------------------------------------------
CREATE VIEW at_risk_features_view AS
SELECT
    s.student_id,
    s.cgpa,
    s.backlogs,
    s.backlogs AS backlog_history,
    s.failed_subjects,
    s.family_income_lpa,

    -- Engagement & attendance risk signals
    att.attendance_percentage,
    att.study_hours_daily,
    att.self_learning_hours,
    att.study_hours_per_week,

    -- Academic fragility
    ar.previous_cgpa,
    ar.previous_semester_percentage,
    ar.previous_subject_avg,
    ar.weak_subject_count,
    ar.subject_consistency,

    -- Component deficits
    em.assignment_completion_rate,
    em.practice_questions,
    em.lowest_subject_score,

    -- Psychological / Lifestyle stressors
    lf.sleep_hours,
    lf.screen_time,
    lf.gaming_hours,
    lf.stress_level,
    lf.burnout_score,
    lf.motivation_level,
    lf.wellness_score,
    lf.screen_to_study_ratio,

    -- Target Ground Truth Label
    s.at_risk_flag AS target_at_risk_flag
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
JOIN exam_marks em ON s.student_id = em.student_id
JOIN attendance att ON s.student_id = att.student_id
JOIN lifestyle lf ON s.student_id = lf.student_id;

-- -----------------------------------------------------------------------------
-- 4. CAREER READINESS VIEW (For Placement & Career Analytics)
-- -----------------------------------------------------------------------------
CREATE VIEW career_readiness_view AS
SELECT
    s.student_id,
    s.cgpa,
    s.backlogs,
    sk.resume_score,
    sk.communication_skills,
    sk.aptitude_score,
    sk.mock_interview_score,
    sk.development_projects_count,
    sk.ai_ml_projects,
    sk.git_hub_repos,
    sk.ai_tool_usage_frequency,
    sk.prompt_engineering_skill,
    cp.hackathons_participated,
    cp.preferred_domain,
    cp.career_goal,

    -- Composite Readiness Index (Weighted score out of 100)
    ROUND(
        (COALESCE(sk.resume_score, 50.0) * 0.20 +
         COALESCE(sk.communication_skills, 50.0) * 0.20 +
         COALESCE(sk.aptitude_score, 50.0) * 0.20 +
         COALESCE(sk.mock_interview_score, 50.0) * 0.20 +
         MIN(COALESCE(sk.development_projects_count, 0) * 10.0, 100.0) * 0.10 +
         MIN(COALESCE(cp.hackathons_participated, 0) * 20.0, 100.0) * 0.10),
        2
    ) AS composite_readiness_score
FROM students s
JOIN skills sk ON s.student_id = sk.student_id
JOIN career_preferences cp ON s.student_id = cp.student_id;

-- -----------------------------------------------------------------------------
-- 5. STAR SCHEMA COMPATIBILITY VIEWS
-- -----------------------------------------------------------------------------
CREATE VIEW dim_student AS
SELECT 
    s.*,
    COALESCE(s.preferred_domain, 'Computer Science') AS stream_branch,
    CASE 
        WHEN s.family_income_lpa >= 10.0 THEN 1
        WHEN s.family_income_lpa >= 5.0 THEN 2
        ELSE 3
    END AS college_tier,
    'Active' AS academic_status
FROM student_360_view s;

CREATE VIEW fact_performance AS
SELECT s.student_id, 'Mathematics' AS subject, ar.previous_subject_avg AS marks, 100.0 AS max_marks, 'academic' AS source FROM students s JOIN academic_records ar ON s.student_id = ar.student_id
UNION ALL
SELECT s.student_id, 'Science' AS subject, em.lowest_subject_score AS marks, 100.0 AS max_marks, 'exam' AS source FROM students s JOIN exam_marks em ON s.student_id = em.student_id
UNION ALL
SELECT s.student_id, 'English' AS subject, em.previous_internal_marks AS marks, 100.0 AS max_marks, 'internal' AS source FROM students s JOIN exam_marks em ON s.student_id = em.student_id
UNION ALL
SELECT s.student_id, 'Overall Score' AS subject, em.previous_midterm_score AS marks, 100.0 AS max_marks, 'midterm' AS source FROM students s JOIN exam_marks em ON s.student_id = em.student_id
UNION ALL
SELECT s.student_id, 'Overall Percentage' AS subject, ar.previous_semester_percentage AS marks, 100.0 AS max_marks, 'semester' AS source FROM students s JOIN academic_records ar ON s.student_id = ar.student_id
UNION ALL
SELECT s.student_id, 'Degree CGPA' AS subject, (s.cgpa * 10.0) AS marks, 100.0 AS max_marks, 'cgpa' AS source FROM students s;

CREATE VIEW fact_lifestyle AS
SELECT * FROM lifestyle;

CREATE VIEW fact_career AS
SELECT * FROM career_readiness_view;
