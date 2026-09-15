-- =============================================================================
-- KDAC-3 PostgreSQL Data Warehouse Schema
-- Student Academic Success, Subject Performance & Career Readiness Platform
-- =============================================================================

-- Drop tables in reverse foreign-key dependency order for idempotency
DROP TABLE IF EXISTS career_preferences CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS lifestyle CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS exam_marks CASCADE;
DROP TABLE IF EXISTS academic_records CASCADE;
DROP TABLE IF EXISTS students CASCADE;

-- -----------------------------------------------------------------------------
-- 1. CENTRAL STUDENTS TABLE (Core Entity)
-- -----------------------------------------------------------------------------
CREATE TABLE students (
    student_id          VARCHAR(16) PRIMARY KEY,
    enrollment_date     DATE,
    family_income_lpa   NUMERIC(6, 2) CHECK (family_income_lpa >= 0.0),
    cgpa                NUMERIC(4, 2) NOT NULL CHECK (cgpa >= 0.0 AND cgpa <= 10.0),
    backlogs            INTEGER NOT NULL DEFAULT 0 CHECK (backlogs >= 0),
    failed_subjects     INTEGER NOT NULL DEFAULT 0 CHECK (failed_subjects >= 0),
    at_risk_flag        INTEGER NOT NULL CHECK (at_risk_flag IN (0, 1)),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_students_at_risk ON students(at_risk_flag);
CREATE INDEX idx_students_cgpa ON students(cgpa);

-- -----------------------------------------------------------------------------
-- 2. ACADEMIC RECORDS TABLE (Historical Course Performance)
-- -----------------------------------------------------------------------------
CREATE TABLE academic_records (
    student_id                      VARCHAR(16) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
    previous_cgpa                   NUMERIC(4, 2) NOT NULL CHECK (previous_cgpa >= 0.0 AND previous_cgpa <= 10.0),
    previous_semester_percentage    NUMERIC(5, 2) NOT NULL CHECK (previous_semester_percentage >= 0.0 AND previous_semester_percentage <= 100.0),
    previous_subject_avg            NUMERIC(5, 2) NOT NULL CHECK (previous_subject_avg >= 0.0 AND previous_subject_avg <= 100.0),
    weak_subject_count              INTEGER NOT NULL DEFAULT 0 CHECK (weak_subject_count >= 0),
    subject_consistency             NUMERIC(5, 2) NOT NULL CHECK (subject_consistency >= 0.0 AND subject_consistency <= 100.0),
    performance_band                VARCHAR(32) NOT NULL CHECK (performance_band IN ('At_Risk', 'Average', 'Good', 'Excellent')),
    updated_at                      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_academic_perf_band ON academic_records(performance_band);
CREATE INDEX idx_academic_prev_cgpa ON academic_records(previous_cgpa);

-- -----------------------------------------------------------------------------
-- 3. EXAM MARKS TABLE (Component Marks & Future Prediction Target)
-- -----------------------------------------------------------------------------
CREATE TABLE exam_marks (
    student_id                      VARCHAR(16) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
    previous_internal_marks         NUMERIC(5, 2) CHECK (previous_internal_marks >= 0.0 AND previous_internal_marks <= 100.0),
    previous_assignment_score       NUMERIC(5, 2) CHECK (previous_assignment_score >= 0.0 AND previous_assignment_score <= 100.0),
    previous_midterm_score          NUMERIC(5, 2) CHECK (previous_midterm_score >= 0.0 AND previous_midterm_score <= 100.0),
    lowest_subject_score            NUMERIC(5, 2) CHECK (lowest_subject_score >= 0.0 AND lowest_subject_score <= 100.0),
    assignment_completion_rate      NUMERIC(5, 2) CHECK (assignment_completion_rate >= 0.0 AND assignment_completion_rate <= 100.0),
    practice_questions              INTEGER CHECK (practice_questions >= 0),
    next_semester_marks             NUMERIC(5, 2) NOT NULL CHECK (next_semester_marks >= 0.0 AND next_semester_marks <= 100.0),
    updated_at                      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_exam_next_marks ON exam_marks(next_semester_marks);

-- -----------------------------------------------------------------------------
-- 4. ATTENDANCE TABLE (Course Engagement & Study Habits)
-- -----------------------------------------------------------------------------
CREATE TABLE attendance (
    student_id                      VARCHAR(16) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
    attendance_percentage           NUMERIC(5, 2) NOT NULL CHECK (attendance_percentage >= 0.0 AND attendance_percentage <= 100.0),
    study_hours_daily               NUMERIC(4, 2) CHECK (study_hours_daily >= 0.0 AND study_hours_daily <= 24.0),
    self_learning_hours             NUMERIC(4, 2) CHECK (self_learning_hours >= 0.0 AND self_learning_hours <= 24.0),
    study_hours_per_week            NUMERIC(5, 2) CHECK (study_hours_per_week >= 0.0 AND study_hours_per_week <= 168.0),
    last_sync_time                  TIMESTAMP WITH TIME ZONE,
    updated_at                      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attendance_pct ON attendance(attendance_percentage);

-- -----------------------------------------------------------------------------
-- 5. LIFESTYLE TABLE (Wellness, Sleep & Psychological Indicators)
-- -----------------------------------------------------------------------------
CREATE TABLE lifestyle (
    student_id                      VARCHAR(16) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
    sleep_hours                     NUMERIC(4, 2) CHECK (sleep_hours >= 0.0 AND sleep_hours <= 24.0),
    screen_time                     NUMERIC(4, 2) CHECK (screen_time >= 0.0 AND screen_time <= 24.0),
    gaming_hours                    NUMERIC(4, 2) CHECK (gaming_hours >= 0.0 AND gaming_hours <= 24.0),
    stress_level                    NUMERIC(4, 2) CHECK (stress_level >= 0.0 AND stress_level <= 10.0),
    burnout_score                   NUMERIC(5, 2) CHECK (burnout_score >= 0.0 AND burnout_score <= 100.0),
    motivation_level                NUMERIC(4, 2) CHECK (motivation_level >= 0.0 AND motivation_level <= 10.0),
    adaptability_score              NUMERIC(5, 2) CHECK (adaptability_score >= 0.0 AND adaptability_score <= 100.0),
    gym_frequency                   INTEGER CHECK (gym_frequency >= 0 AND gym_frequency <= 7),
    wellness_score                  NUMERIC(5, 2) CHECK (wellness_score >= 0.0 AND wellness_score <= 100.0),
    screen_to_study_ratio           NUMERIC(6, 2) CHECK (screen_to_study_ratio >= 0.0),
    extracurricular_hours           NUMERIC(4, 2) CHECK (extracurricular_hours >= 0.0 AND extracurricular_hours <= 24.0),
    survey_date                     DATE,
    updated_at                      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lifestyle_wellness ON lifestyle(wellness_score);
CREATE INDEX idx_lifestyle_stress ON lifestyle(stress_level);

-- -----------------------------------------------------------------------------
-- 6. SKILLS TABLE (Placement Readiness & Technical Capabilities)
-- -----------------------------------------------------------------------------
CREATE TABLE skills (
    student_id                      VARCHAR(16) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
    resume_score                    NUMERIC(5, 2) CHECK (resume_score >= 0.0 AND resume_score <= 100.0),
    communication_skills            NUMERIC(5, 2) CHECK (communication_skills >= 0.0 AND communication_skills <= 100.0),
    aptitude_score                  NUMERIC(5, 2) CHECK (aptitude_score >= 0.0 AND aptitude_score <= 100.0),
    mock_interview_score            NUMERIC(5, 2) CHECK (mock_interview_score >= 0.0 AND mock_interview_score <= 100.0),
    development_projects_count      INTEGER NOT NULL DEFAULT 0 CHECK (development_projects_count >= 0),
    ai_ml_projects                  INTEGER NOT NULL DEFAULT 0 CHECK (ai_ml_projects >= 0),
    git_hub_repos                   INTEGER NOT NULL DEFAULT 0 CHECK (git_hub_repos >= 0),
    ai_tool_usage_frequency         NUMERIC(4, 2) CHECK (ai_tool_usage_frequency >= 0.0 AND ai_tool_usage_frequency <= 10.0),
    prompt_engineering_skill        NUMERIC(5, 2) CHECK (prompt_engineering_skill >= 0.0 AND prompt_engineering_skill <= 100.0),
    updated_at                      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skills_resume ON skills(resume_score);

-- -----------------------------------------------------------------------------
-- 7. CAREER PREFERENCES TABLE (Goals, Domains & Hackathons)
-- -----------------------------------------------------------------------------
CREATE TABLE career_preferences (
    student_id                      VARCHAR(16) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
    hackathons_participated         INTEGER NOT NULL DEFAULT 0 CHECK (hackathons_participated >= 0),
    preferred_domain                VARCHAR(64),
    career_goal                     VARCHAR(64),
    submitted_at                    TIMESTAMP WITH TIME ZONE,
    updated_at                      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_career_domain ON career_preferences(preferred_domain);
CREATE INDEX idx_career_goal ON career_preferences(career_goal);
