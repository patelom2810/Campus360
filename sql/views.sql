-- =============================================================================
-- KDAC-3 Analytical Views
-- Designed for Dashboards, Model Feature Engineering & Faculty 360 Profiling
-- =============================================================================

-- Drop existing views in reverse order
DROP VIEW IF EXISTS career_readiness_view CASCADE;
DROP VIEW IF EXISTS at_risk_features_view CASCADE;
DROP VIEW IF EXISTS performance_features_view CASCADE;
DROP VIEW IF EXISTS student_360_view CASCADE;

-- -----------------------------------------------------------------------------
-- 1. STUDENT 360 HOLISTIC VIEW
-- Denormalized master view combining all 7 warehouse domains per student
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW student_360_view AS
SELECT
    -- Core Student Demographics
    s.student_id,
    s.enrollment_date,
    s.family_income_lpa,
    s.cgpa,
    s.backlogs,
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
-- STRICTLY ZERO DATA LEAKAGE: Excludes next_semester_marks and performance_band
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW performance_features_view AS
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

    -- Target variable (clearly separated for ML training ingestion)
    em.next_semester_marks AS target_next_semester_marks
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
JOIN exam_marks em ON s.student_id = em.student_id
JOIN attendance att ON s.student_id = att.student_id
JOIN lifestyle lf ON s.student_id = lf.student_id;


-- -----------------------------------------------------------------------------
-- 3. AT-RISK FEATURES VIEW (For Model 2: Screening Classification)
-- Combines academic risk signals, attendance deficits, and lifestyle stressors
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW at_risk_features_view AS
SELECT
    s.student_id,
    s.cgpa,
    s.backlogs,
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
CREATE OR REPLACE VIEW career_readiness_view AS
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
         LEAST(sk.development_projects_count * 10.0, 100.0) * 0.10 +
         LEAST(cp.hackathons_participated * 20.0, 100.0) * 0.10)::numeric,
        2
    ) AS composite_readiness_score
FROM students s
JOIN skills sk ON s.student_id = sk.student_id
JOIN career_preferences cp ON s.student_id = cp.student_id;
