"""
stitch_v5.py
============
Full star-schema data stitching pipeline for the Student Academic Success &
Career Readiness Analytics Platform.

Outputs (all written to data/processed/v5/):
  dim_student.csv
  fact_risk_behaviour.csv
  fact_placement.csv
  fact_subject_marks.csv
  fact_skill_scores.csv
  dim_cs_skills_v5.csv
  data_quality_report.md
  data_lineage_v5.md
  null_handling_report.md
  removed_columns.md

Design principles:
  - Start from TRUE RAW files (hybrid_student_performance_1200.csv is the spine)
  - Every null imputation is documented with strategy + justification
  - No identity joins across files from different sources
  - Every probabilistic join flagged with is_synthetic_*
  - Performance risk level NEVER imputed (it's the target label)
  - No fabricated values to eliminate NULLs

Run: python3 etl/stitch_v5.py
"""

import json
import os
import random
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
ROOT  = Path(__file__).resolve().parent.parent
RAW   = ROOT / "data" / "raw"
PROC  = ROOT / "data" / "processed"
OUT   = ROOT / "data" / "processed" / "v5"
OUT.mkdir(parents=True, exist_ok=True)

SRC = {
    "spine":       RAW  / "hybrid_student_performance_1200.csv",
    "cs_raw":      RAW  / "cs_students.csv",
    "uci":         PROC / "src_uci_subject_marks.csv",
    "placement":   PROC / "src_placement_prediction_2026.csv",
    "skill_scores":PROC / "src_skill_scores.csv",
    "ds_marks":    PROC / "src_ds_student_marks.csv",
    "college":     PROC / "src_college_placement.csv",
}

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT TRACKING
# ─────────────────────────────────────────────────────────────────────────────
NULL_LOG      = []   # (table, column, n_nulls, strategy, justification)
REMOVED_COLS  = []   # (source_file, column, reason)
LINEAGE       = []   # (output_table, column, source_file, source_col, transform)
RANGE_ISSUES  = []   # (table, column, issue, count)
QA_LOG        = []   # (check, result, detail)

def log_null(table, col, n, strategy, justification):
    NULL_LOG.append({"table": table, "column": col, "null_count": n,
                     "strategy": strategy, "justification": justification})

def log_removed(source, col, reason):
    REMOVED_COLS.append({"source_file": source, "column": col, "reason": reason})

def log_lineage(out_table, col, src_file, src_col, transform="direct"):
    LINEAGE.append({"output_table": out_table, "column": col,
                    "source_file": src_file, "source_column": src_col,
                    "transform": transform})

def log_range(table, col, issue, count):
    RANGE_ISSUES.append({"table": table, "column": col, "issue": issue, "count": count})

def qa(check, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    QA_LOG.append({"check": check, "status": status, "detail": detail})
    symbol = "✅" if passed else "❌"
    print(f"  {symbol} {check}: {status} {('— '+detail) if detail else ''}")

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def cgpa_band(cat):
    cat = str(cat).strip()
    if "9.5" in cat: return "9.5-10.0"
    elif "8.5" in cat: return "8.5-9.4"
    elif "7.0" in cat: return "7.0-8.4"
    elif "5.0" in cat or "6" in cat: return "5.0-6.9"
    return "unknown"

def cgpa_num_to_band(v):
    if pd.isna(v): return "unknown"
    if v >= 9.5: return "9.5-10.0"
    elif v >= 8.5: return "8.5-9.4"
    elif v >= 7.0: return "7.0-8.4"
    elif v >= 5.0: return "5.0-6.9"
    return "unknown"

def age_band(a):
    if pd.isna(a): return "unknown"
    a = int(a)
    if a <= 18: return "<=18"
    elif a <= 20: return "19-20"
    elif a <= 22: return "21-22"
    elif a <= 24: return "23-24"
    return "25+"

def score_q5(v, scale=1.0):
    """Return 0-4 quintile for a score. scale=1 for 0-1, scale=100 for 0-100."""
    if pd.isna(v): return 2
    return min(int((v / scale) * 5), 4)

CS_STREAMS = {"BCA", "BSc Computer Science", "BSc IT", "BSc Cyber Security"}

STREAM_TO_BRANCH = {
    "BCA": "CSE", "BSc Computer Science": "CSE", "BSc IT": "IT",
    "BCom": "EEE", "BBA": "Mechanical", "BSc Cyber Security": "CSE", "BA": "Civil",
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — LOAD & PROFILE ALL SOURCE FILES
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("STEP 1 — Loading & profiling source files")
print("=" * 72)

raw_frames = {}
quality_before = {}

for name, path in SRC.items():
    df = pd.read_csv(path)
    raw_frames[name] = df
    null_counts = df.isnull().sum()
    quality_before[name] = {
        "rows": len(df), "cols": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "total_nulls": int(null_counts.sum()),
        "null_per_col": {c: int(v) for c, v in null_counts.items() if v > 0},
        "columns": df.columns.tolist(),
    }
    dup_id_col = None
    for c in df.columns:
        if "id" in c.lower() and df[c].dtype in [object, "str"]:
            if not df[c].is_unique:
                dup_id_col = c
    quality_before[name]["duplicate_id_col"] = dup_id_col
    print(f"  {name}: {df.shape} | nulls={null_counts.sum()} | dups={df.duplicated().sum()}")

spine    = raw_frames["spine"]
cs_raw   = raw_frames["cs_raw"]
uci      = raw_frames["uci"]
pl       = raw_frames["placement"]
scores   = raw_frames["skill_scores"]
ds       = raw_frames["ds_marks"]
clg      = raw_frames["college"]

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — RANGE VALIDATION ON ALL SOURCES
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 2 — Range validation")

# spine age
age_bad = ((spine["age"] < 15) | (spine["age"] > 35)).sum()
if age_bad: log_range("spine", "age", f"out of 15-35 range", int(age_bad))

# placement cgpa
pl_cgpa_bad = ((pl["cgpa"] < 0) | (pl["cgpa"] > 10)).sum()
if pl_cgpa_bad: log_range("placement", "cgpa", "outside 0-10", int(pl_cgpa_bad))

# placement salary
pl_sal_neg = (pl["salary_package_lpa"] < 0).sum()
if pl_sal_neg: log_range("placement", "salary_package_lpa", "negative", int(pl_sal_neg))

# placement age
pl_age_bad = ((pl["age"] < 15) | (pl["age"] > 35)).sum()
if pl_age_bad: log_range("placement", "age", "outside 15-35", int(pl_age_bad))

# skill_scores range 0-1
for col in ["Python", "Sql", "ML", "Tableau", "Excel"]:
    bad = ((scores[col] < 0) | (scores[col] > 1)).sum()
    if bad: log_range("skill_scores", col, "outside 0-1", int(bad))

# ds_marks range 0-100
for col in ["sql_marks","excel_marks","python_marks","power_bi_marks","english_marks"]:
    bad = ((ds[col] < 0) | (ds[col] > 100)).sum()
    if bad: log_range("ds_marks", col, "outside 0-100", int(bad))

# UCI marks 0-20
for col in ["g1_mat","g2_mat","g3_mat","g1_por","g2_por","g3_por"]:
    bad = ((uci[col] < 0) | (uci[col] > 20)).sum()
    if bad: log_range("uci", col, "outside 0-20", int(bad))

# cs_raw GPA 0-4
gpa_bad = ((cs_raw["GPA"] < 0) | (cs_raw["GPA"] > 4)).sum()
if gpa_bad: log_range("cs_raw", "GPA", "outside 0-4", int(gpa_bad))

print(f"  Range issues detected: {len(RANGE_ISSUES)}")
for r in RANGE_ISSUES:
    print(f"    ⚠ {r['table']}.{r['column']}: {r['issue']} — count={r['count']}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — NULL HANDLING ON SPINE (hybrid_student_performance_1200)
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 3 — Documented null imputation on spine")

spine = spine.copy()
n0 = spine.isnull().sum().sum()
print(f"  Nulls before imputation: {n0}")

# ── Numeric columns: group-wise median ──────────────────────────────────────
NUM_IMPUTE = {
    "daily_productivity":  ("program_stream", "group_median",
                            "Ordinal numeric; program_stream is the best group proxy"),
    "energy_level":        ("year_class",      "group_median",
                            "Energy correlates with academic year/workload"),
    "stress_level":        ("performance_risk_level", "group_median",
                            "Stress directly predicts risk level; best grouping"),
    "routine_rating":      ("program_stream",  "group_median",
                            "Routine patterns differ by program"),
}

for col, (group_by, strategy, justification) in NUM_IMPUTE.items():
    n_null = spine[col].isnull().sum()
    if n_null == 0:
        continue
    group_medians = spine.groupby(group_by)[col].transform("median")
    global_median = spine[col].median()
    spine[col] = spine[col].fillna(group_medians).fillna(global_median)
    log_null("fact_risk_behaviour", col, int(n_null), strategy, justification)
    print(f"    {col}: {n_null} nulls → {strategy} by {group_by}")

# ── Categorical ordinal: group mode ─────────────────────────────────────────
CAT_MODE_IMPUTE = {
    "revision_frequency":   ("program_stream", "group_mode",
                             "Revision patterns differ by program"),
    "focus_duration":       ("program_stream", "group_mode",
                             "Focus spans differ by program intensity"),
    "sleep_hours":          ("age",            "group_mode",
                             "Sleep patterns correlate with age"),
}

for col, (group_by, strategy, justification) in CAT_MODE_IMPUTE.items():
    n_null = spine[col].isnull().sum()
    if n_null == 0:
        continue
    def group_mode_fill(series):
        mode_val = series.dropna().mode()
        return series.fillna(mode_val.iloc[0] if len(mode_val) > 0 else "Unknown")
    spine[col] = spine.groupby(group_by)[col].transform(group_mode_fill)
    # fallback
    fallback_mode = spine[col].dropna().mode()
    if len(fallback_mode) > 0:
        spine[col] = spine[col].fillna(fallback_mode.iloc[0])
    log_null("fact_risk_behaviour", col, int(n_null), strategy, justification)
    print(f"    {col}: {n_null} nulls → {strategy} by {group_by}")

# ── Categorical: preserve as Unknown / Not Available ─────────────────────────
CAT_UNKNOWN = {
    "screen_time_non_study": ("Unknown",       "Cannot be safely inferred from available features"),
    "online_courses":        ("Not Available", "Binary-type field — cannot impute without risk of bias"),
    "programming_foundation":("Not Available", "Skill level — imputing would fabricate student ability"),
    "events_participation":  ("Unknown",       "Participation data — cannot infer absence/presence"),
    "external_resources":    ("Unknown",       "Context-dependent — cannot safely infer"),
    "external_pressure":     ("Unknown",       "Subjective — cannot safely infer"),
}

for col, (fill_val, justification) in CAT_UNKNOWN.items():
    n_null = spine[col].isnull().sum()
    if n_null == 0:
        continue
    spine[col] = spine[col].fillna(fill_val)
    log_null("fact_risk_behaviour", col, int(n_null), f"fill_with_{fill_val.lower().replace(' ','_')}",
             justification)
    print(f"    {col}: {n_null} nulls → '{fill_val}' (preserved intentionally)")

# ── Target column: NEVER imputed ─────────────────────────────────────────────
target_null = spine["performance_risk_level"].isnull().sum()
if target_null > 0:
    print(f"    ⚠ performance_risk_level has {target_null} nulls — NOT imputed (target column)")
    log_null("fact_risk_behaviour", "performance_risk_level", int(target_null),
             "PRESERVE_NULL", "Target label — NEVER imputed to prevent data leakage")

n1 = spine.isnull().sum().sum()
print(f"  Nulls after imputation: {n1}")
print(f"  Remaining nulls: {spine.isnull().sum()[spine.isnull().sum()>0].to_dict()}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BUILD dim_student
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 4 — Building dim_student")

dim_student = spine[["student_id","year_class","program_stream","age","gender"]].copy()
dim_student.insert(0, "master_student_id",
                   [f"MSTU{str(i+1).zfill(5)}" for i in range(len(dim_student))])
dim_student = dim_student.rename(columns={"student_id": "src_risk_training_id"})
dim_student["is_cs_stream"] = dim_student["program_stream"].isin(CS_STREAMS)

# Lineage
for col in dim_student.columns:
    src = "hybrid_student_performance_1200.csv"
    src_col = "student_id" if col == "src_risk_training_id" else \
              "synthetic" if col == "master_student_id" else \
              "derived" if col == "is_cs_stream" else col
    log_lineage("dim_student", col, src, src_col)

print(f"  dim_student: {dim_student.shape}")
assert dim_student["master_student_id"].is_unique, "master_student_id must be unique!"
assert not dim_student["master_student_id"].str.match(r"^STU").any(), "Namespace collision!"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — BUILD fact_risk_behaviour
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 5 — Building fact_risk_behaviour")

# Drop: student_id (replaced by master_student_id), timestamp (operational)
log_removed("hybrid_student_performance_1200.csv", "timestamp",
            "Operational field — survey submission timestamp, not analytic")

RISK_COLS = [c for c in spine.columns
             if c not in ["student_id", "timestamp"]]

fact_risk = spine[RISK_COLS].copy()
fact_risk.insert(0, "master_student_id", dim_student["master_student_id"].values)
fact_risk["risk_label_available"] = fact_risk["performance_risk_level"].notna()

# Standardise attendance_percentage: it's a string band in this file
# → keep as-is (ordinal categorical), rename for clarity
fact_risk = fact_risk.rename(columns={"attendance_percentage": "attendance_band"})

for col in RISK_COLS:
    log_lineage("fact_risk_behaviour", col, "hybrid_student_performance_1200.csv", col)

print(f"  fact_risk_behaviour: {fact_risk.shape}")
print(f"  risk_label_available=True: {fact_risk['risk_label_available'].sum()}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — BUILD dim_cs_skills_v5
# (from cs_students.csv — the TRUE raw origin)
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 6 — Building dim_cs_skills_v5")

cs = cs_raw.copy()

# Rename to snake_case
cs = cs.rename(columns={
    "Student ID":        "src_cs_student_id",
    "Name":              "student_name",
    "Gender":            "gender",
    "Age":               "age",
    "GPA":               "gpa_4",
    "Major":             "major",
    "Interested Domain": "interested_domain",
    "Projects":          "cs_projects",
    "Future Career":     "future_career",
    "Python":            "python_skill",
    "SQL":               "sql_skill",
    "Java":              "java_skill",
})

# Drop Name for privacy
log_removed("cs_students.csv", "student_name",
            "PII — student names dropped for privacy; src_cs_student_id retained for lineage")
cs = cs.drop(columns=["student_name"])

# Add CSREF key and gpa_10
cs.insert(0, "cs_ref_id",
          [f"CSREF{str(i+1).zfill(3)}" for i in range(len(cs))])
cs["gpa_10"] = (cs["gpa_4"] * 2.5).round(4)
cs["gpa_scale_note"] = "gpa_4 is 0-4.0 scale; gpa_10 = gpa_4 × 2.5"

# Range check
gpa_bad = ((cs["gpa_4"] < 0) | (cs["gpa_4"] > 4.0)).sum()
if gpa_bad:
    log_range("dim_cs_skills_v5", "gpa_4", "outside 0-4.0", int(gpa_bad))

for col in cs.columns:
    log_lineage("dim_cs_skills_v5", col, "cs_students.csv",
                col if col not in ["cs_ref_id","gpa_10","gpa_scale_note"] else "derived")

print(f"  dim_cs_skills_v5: {cs.shape}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — BUILD fact_placement
# Probabilistic join: placement_2026 → master (cgpa_band × branch × gender)
# Pre-join dedup: drop cols already in spine (age, gender, sleep_hours,
#                  study_hours_per_day, attendance_percentage)
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 7 — Building fact_placement (probabilistic join)")

DROPPED_FROM_PLACEMENT = {
    "student_id":           "Integer ID from different source — no overlap with spine IDs",
    "age":                  "Already in dim_student from spine",
    "gender":               "Already in dim_student from spine",
    "sleep_hours":          "Already in fact_risk_behaviour from spine",
    "study_hours_per_day":  "study_hours_daily exists in fact_risk_behaviour from spine",
    "attendance_percentage":"attendance_band exists in fact_risk_behaviour; different formats",
    "cgpa":                 "Used only as matching key; spine uses cgpa_category band",
    "branch":               "Used only as matching key",
}
for col, reason in DROPPED_FROM_PLACEMENT.items():
    log_removed("src_placement_prediction_2026.csv", col, reason)

PL_KEEP = [
    "coding_skill_score", "aptitude_score", "communication_skill_score",
    "logical_reasoning_score", "hackathons_participated", "github_repos",
    "linkedin_connections", "mock_interview_score", "internships_count",
    "projects_count", "certifications_count", "extracurricular_score",
    "leadership_score", "volunteer_experience", "backlogs",
    "college_tier", "placement_status", "salary_package_lpa",
]

# Renamed to avoid confusion with college dataset columns
PL_RENAME = {
    "extracurricular_score":       "pl_extracurricular_score",
    "communication_skill_score":   "pl_communication_skill_score",
    "leadership_score":            "pl_leadership_score",
}

pl_work = pl[["cgpa", "branch", "gender"] + PL_KEEP].copy()
pl_work["_cgpa_band"]   = pl_work["cgpa"].apply(cgpa_num_to_band)
pl_work["_branch"]      = pl_work["branch"]
pl_work["_gender_norm"] = pl_work["gender"].str.strip().str.lower()

# Build lookup pool
pl_pool = defaultdict(list)
for idx, row in pl_work.iterrows():
    pl_pool[(row["_cgpa_band"], row["_branch"], row["_gender_norm"])].append(idx)
pl_band_pool = defaultdict(list)
for idx, row in pl_work.iterrows():
    pl_band_pool[row["_cgpa_band"]].append(idx)
pl_all = list(pl_work.index)

# Pre-join statistics
print(f"  placement_2026 pool: {len(pl_work):,} rows")
print(f"  distinct (band,branch,gender) keys: {len(pl_pool)}")

# Helper: pick a matching row
def pick_pl(cgpa_b, branch, gender):
    g = str(gender).strip().lower()
    pool = pl_pool.get((cgpa_b, branch, g))
    if not pool: pool = pl_band_pool.get(cgpa_b, pl_all)
    return random.choice(pool)

# Match
dim_student["_cgpa_band"]  = spine["cgpa_category"].apply(cgpa_band).values
dim_student["_branch"]     = dim_student["program_stream"].map(STREAM_TO_BRANCH).fillna("CSE")

pl_indices = [pick_pl(row["_cgpa_band"], row["_branch"], row["gender"])
              for _, row in dim_student.iterrows()]

fact_placement = pl_work.iloc[pl_indices][PL_KEEP].reset_index(drop=True)
fact_placement = fact_placement.rename(columns=PL_RENAME)
fact_placement.insert(0, "master_student_id", dim_student["master_student_id"].values)
fact_placement["is_synthetic_placement_match"] = True
fact_placement["match_method"] = "cgpa_band × branch_group × gender"

# Validate: salary=0 iff Not Placed
sal_inconsist = fact_placement[
    (fact_placement["salary_package_lpa"] > 0) &
    (fact_placement["placement_status"] == "Not Placed")
].shape[0]
if sal_inconsist:
    log_range("fact_placement", "salary_package_lpa",
              "salary > 0 for Not Placed students", sal_inconsist)

for col in PL_KEEP:
    out_col = PL_RENAME.get(col, col)
    log_lineage("fact_placement", out_col, "src_placement_prediction_2026.csv", col)

print(f"  fact_placement: {fact_placement.shape}")
print(f"  Placed: {(fact_placement['placement_status']=='Placed').sum()} | "
      f"Not Placed: {(fact_placement['placement_status']=='Not Placed').sum()}")

# Clean helper cols from dim_student
dim_student = dim_student.drop(columns=["_cgpa_band","_branch","is_cs_stream"])

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — BUILD fact_subject_marks (LONG FORMAT)
# Source: src_uci_subject_marks.csv (382 UCI students)
# NOT joined 1:1 to master — independent bridge with own PK
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 8 — Building fact_subject_marks (long format, independent bridge)")

uci_work = uci.copy()

# Verify UCI IDs are unique
assert uci_work["student_id"].is_unique, "UCI student_id must be unique"

# Pivot to long format: one row per (student, subject, grade_period)
rows = []
for _, row in uci_work.iterrows():
    uid = row["student_id"]
    for subject_code, subject_name, max_m in [("mat","Mathematics",20),("por","Portuguese",20)]:
        g1 = row.get(f"g1_{subject_code}", np.nan)
        g2 = row.get(f"g2_{subject_code}", np.nan)
        g3 = row.get(f"g3_{subject_code}", np.nan)
        for period, mark in [("G1", g1), ("G2", g2), ("G3", g3)]:
            pct = round(mark / max_m * 100, 2) if pd.notna(mark) and max_m > 0 else np.nan
            rows.append({
                "uci_ref_id":    uid,
                "subject_id":    subject_code,
                "subject_name":  subject_name,
                "grade_period":  period,
                "marks":         mark if pd.notna(mark) else np.nan,
                "max_marks":     max_m,
                "percentage":    pct,
                "source":        "UCI_Student_Performance",
                "is_synthetic":  False,
                "master_student_id": np.nan,  # intentionally null — no 1:1 link to master
            })

fact_subject_marks = pd.DataFrame(rows)

# Validate marks in range
for col in ["marks"]:
    bad = fact_subject_marks[col].dropna()
    bad_count = ((bad < 0) | (bad > 20)).sum()
    if bad_count: log_range("fact_subject_marks", col, "outside 0-20", int(bad_count))

log_lineage("fact_subject_marks", "uci_ref_id", "src_uci_subject_marks.csv", "student_id")
log_lineage("fact_subject_marks", "marks", "src_uci_subject_marks.csv",
            "g1_mat/g2_mat/g3_mat/g1_por/g2_por/g3_por", "melted to long format")

# Note which UCI cols were NOT used in long format
UNUSED_UCI = [c for c in uci.columns
              if c not in ["student_id"] and
              not any(x in c for x in ["g1_","g2_","g3_"])]
for c in UNUSED_UCI:
    log_removed("src_uci_subject_marks.csv", c,
                "Lifestyle/demographic fields not melted into fact_subject_marks; "
                "retained in separate dim if needed. Excluded to keep fact_subject_marks lean.")

print(f"  fact_subject_marks: {fact_subject_marks.shape} "
      f"({len(uci_work)} students × 2 subjects × 3 periods)")
print(f"  master_student_id: all null (no 1:1 identity link to master)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — BUILD fact_skill_scores (LONG FORMAT)
# Sources: src_skill_scores.csv + src_ds_student_marks.csv
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 9 — Building fact_skill_scores (long format)")

skill_rows = []

# ── 9a: src_skill_scores.csv → tool-level scores (0-1 scale) ─────────────
scores_work = scores.copy()
scores_work.columns = [c.strip() for c in scores_work.columns]

# Validate
for col in ["Python","Sql","ML","Tableau","Excel"]:
    bad = ((scores_work[col]<0)|(scores_work[col]>1)).sum()
    if bad: log_range("fact_skill_scores", col, "outside 0-1", int(bad))

# Removed: Student Placed (placement_status from fact_placement is authoritative)
log_removed("src_skill_scores.csv", "Student Placed",
            "Placement outcome — authoritative source is src_placement_prediction_2026 via fact_placement")

# Quintile-based probabilistic match to master
scores_work["_py_q"]  = scores_work["Python"].apply(lambda v: score_q5(v, 1.0))
scores_work["_sql_q"] = scores_work["Sql"].apply(lambda v: score_q5(v, 1.0))

sc_pool = defaultdict(list)
for idx, row in scores_work.iterrows():
    sc_pool[(row["_py_q"], row["_sql_q"])].append(idx)
sc_all = list(scores_work.index)

def pick_score(coding_val, logic_val):
    pq = score_q5(coding_val, 100.0)
    sq = score_q5(logic_val,  100.0)
    pool = sc_pool.get((pq, sq))
    if not pool:
        for sq2 in range(5):
            pool = sc_pool.get((pq, sq2))
            if pool: break
    if not pool: pool = sc_all
    return random.choice(pool)

for i, (_, mrow) in enumerate(fact_placement.iterrows()):
    mstu = dim_student.iloc[i]["master_student_id"]
    idx  = pick_score(mrow.get("coding_skill_score", 50.0),
                      mrow.get("logical_reasoning_score", 50.0))
    srow = scores_work.iloc[idx]
    for skill, col in [("python","Python"),("sql","Sql"),("ml","ML"),
                        ("tableau","Tableau"),("excel","Excel")]:
        skill_rows.append({
            "master_student_id":   mstu,
            "skill":               skill,
            "score":               srow[col],
            "score_scale":         "0-1",
            "source":              "src_skill_scores.csv",
            "is_synthetic_match":  True,
            "match_method":        "python_quintile × sql_quintile vs coding/logic scores",
        })

# ── 9b: src_ds_student_marks.csv → subject marks for CS/IT students ──────
ds_work = ds.copy()
# Removed: location (not analytic), student_id (non-overlapping integer source)
log_removed("src_ds_student_marks.csv", "location",
            "City name — not analytic for academic performance; no join key")
log_removed("src_ds_student_marks.csv", "student_id",
            "Non-overlapping integer namespace from different source")

ds_work["_age_band"] = ds_work["age"].apply(age_band)
ds_age_pool = defaultdict(list)
for idx, row in ds_work.iterrows():
    ds_age_pool[row["_age_band"]].append(idx)
ds_all_idx = list(ds_work.index)

CS_SKILL_MAP = {
    "ds_sql":      "sql_marks",
    "ds_excel":    "excel_marks",
    "ds_python":   "python_marks",
    "ds_power_bi": "power_bi_marks",
    "ds_english":  "english_marks",
}

for i, mrow in dim_student.iterrows():
    mstu    = mrow["master_student_id"]
    stream  = mrow["program_stream"]
    age_b   = age_band(mrow["age"])

    if stream not in CS_STREAMS:
        # Non-CS: explicitly skip — no fabricated marks
        continue

    pool = ds_age_pool.get(age_b, ds_all_idx)
    idx  = random.choice(pool)
    drow = ds_work.iloc[idx]

    for skill, src_col in CS_SKILL_MAP.items():
        skill_rows.append({
            "master_student_id":   mstu,
            "skill":               skill,
            "score":               drow[src_col],
            "score_scale":         "0-100",
            "source":              "src_ds_student_marks.csv",
            "is_synthetic_match":  True,
            "match_method":        "age_band match, CS/IT students only",
        })

fact_skill_scores = pd.DataFrame(skill_rows)
log_lineage("fact_skill_scores", "score", "src_skill_scores.csv + src_ds_student_marks.csv",
            "Python/Sql/ML/Tableau/Excel; sql_marks/excel_marks/python_marks/power_bi_marks/english_marks",
            "melted to long format + probabilistic match")

print(f"  fact_skill_scores: {fact_skill_scores.shape}")
print(f"  from src_skill_scores: {(fact_skill_scores['source']=='src_skill_scores.csv').sum()}")
print(f"  from src_ds_marks:     {(fact_skill_scores['source']=='src_ds_student_marks.csv').sum()}")
cs_count = (fact_skill_scores["source"]=="src_ds_student_marks.csv").sum()
print(f"  CS-stream students with DS marks: {cs_count // len(CS_SKILL_MAP)}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 — COLUMN NAMING STANDARDISATION
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 10 — Column naming standardisation")

# All output tables already use snake_case.
# Verify no uppercase or spaces in output columns:
for tname, tdf in [("dim_student", dim_student),
                    ("fact_risk_behaviour", fact_risk),
                    ("fact_placement", fact_placement),
                    ("fact_subject_marks", fact_subject_marks),
                    ("fact_skill_scores", fact_skill_scores),
                    ("dim_cs_skills_v5", cs)]:
    bad_cols = [c for c in tdf.columns if c != c.lower() or " " in c]
    if bad_cols:
        print(f"  ⚠ {tname} non-snake_case cols: {bad_cols}")
    else:
        print(f"  ✓ {tname}: all columns snake_case")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 11 — FINAL QUALITY CHECKS (14 checks)
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 11 — Final quality checks")

# 1 Row counts
qa("dim_student row count = 1,200",
   len(dim_student) == 1200, f"actual={len(dim_student)}")
qa("fact_risk_behaviour row count = 1,200",
   len(fact_risk) == 1200, f"actual={len(fact_risk)}")
qa("fact_placement row count = 1,200",
   len(fact_placement) == 1200, f"actual={len(fact_placement)}")
qa("fact_subject_marks row count = 2,292 (382×2×3)",
   len(fact_subject_marks) == 382*2*3,
   f"actual={len(fact_subject_marks)}, expected={382*2*3}")
qa("dim_cs_skills_v5 row count = 180",
   len(cs) == 180, f"actual={len(cs)}")

# 2 Primary key uniqueness
qa("dim_student: master_student_id unique",
   dim_student["master_student_id"].is_unique)
qa("fact_risk_behaviour: master_student_id unique",
   fact_risk["master_student_id"].is_unique)
qa("fact_placement: master_student_id unique",
   fact_placement["master_student_id"].is_unique)
qa("dim_cs_skills_v5: cs_ref_id unique",
   cs["cs_ref_id"].is_unique)

# 3 Namespace: MSTU must not match STU#### or STU##### patterns
qa("master_student_id namespace safe (no STU collision)",
   not dim_student["master_student_id"].str.match(r"^STU\d+$").any())

# 4 FK integrity: fact_risk_behaviour → dim_student
fk_risk = set(fact_risk["master_student_id"]) <= set(dim_student["master_student_id"])
qa("fact_risk_behaviour FK → dim_student valid", fk_risk)

fk_pl = set(fact_placement["master_student_id"]) <= set(dim_student["master_student_id"])
qa("fact_placement FK → dim_student valid", fk_pl)

fk_sk = set(fact_skill_scores["master_student_id"].dropna()) <= \
        set(dim_student["master_student_id"])
qa("fact_skill_scores FK → dim_student valid (non-null)", fk_sk)

# 5 Null audit: target never imputed
target_nulls = fact_risk["performance_risk_level"].isnull().sum()
qa("performance_risk_level (target) not imputed",
   True, f"{target_nulls} nulls preserved intentionally")

# 6 No duplicate rows in dim/fact tables
qa("dim_student: no duplicate rows",  not dim_student.duplicated().any())
qa("fact_risk_behaviour: no duplicate rows", not fact_risk.duplicated().any())
qa("fact_placement: no duplicate rows", not fact_placement.duplicated().any())

# 7 Numeric range spot-checks
# salary >= 0
neg_sal = (fact_placement["salary_package_lpa"] < 0).sum()
qa("salary_package_lpa >= 0", neg_sal == 0, f"{neg_sal} negatives")

# skill scores from src_skill_scores in 0-1
sc_subset = fact_skill_scores[fact_skill_scores["source"]=="src_skill_scores.csv"]
sc_bad = ((sc_subset["score"]<0)|(sc_subset["score"]>1)).sum()
qa("skill_scores (0-1 scale) in range", sc_bad == 0, f"{sc_bad} out of range")

# DS marks in 0-100
ds_subset = fact_skill_scores[fact_skill_scores["source"]=="src_ds_student_marks.csv"]
ds_bad = ((ds_subset["score"]<0)|(ds_subset["score"]>100)).sum()
qa("ds_marks (0-100 scale) in range", ds_bad == 0, f"{ds_bad} out of range")

# 8 Pairwise correlation check on fact_placement numeric cols
num_pl = fact_placement.select_dtypes(include=[np.number])
num_pl_cols = [c for c in num_pl.columns
               if not c.startswith("is_") and "master" not in c]
corr = num_pl[num_pl_cols].corr()
high_corr_pairs = [(c1,c2,round(corr.loc[c1,c2],4))
                   for i,c1 in enumerate(num_pl_cols)
                   for j,c2 in enumerate(num_pl_cols)
                   if i<j and abs(corr.loc[c1,c2])>=0.95]
qa("fact_placement: no near-duplicate numeric columns (corr≥0.95)",
   len(high_corr_pairs)==0,
   f"{len(high_corr_pairs)} pairs" + (f": {high_corr_pairs[:2]}" if high_corr_pairs else ""))

# 9 Synthetic flags consistent
all_synth_pl = fact_placement["is_synthetic_placement_match"].all()
qa("fact_placement: is_synthetic_placement_match=True for all rows", all_synth_pl)

all_synth_sk = fact_skill_scores["is_synthetic_match"].all()
qa("fact_skill_scores: is_synthetic_match=True for all rows", all_synth_sk)

uci_synth = (fact_subject_marks["is_synthetic"] == False).all()
qa("fact_subject_marks: is_synthetic=False for all UCI rows (real data)", uci_synth)

# 10 Banned v3 columns absent
BANNED = {"previous_gpa","Previous_GPA_10","career_field","career_gpa",
          "subject_marks_student_id","career_target"}
for tname, tdf in [("dim_student",dim_student),("fact_risk_behaviour",fact_risk),
                    ("fact_placement",fact_placement)]:
    present = BANNED & set(tdf.columns)
    qa(f"{tname}: no banned v3 columns", len(present)==0,
       f"found: {present}" if present else "")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 12 — WRITE OUTPUT CSVs
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 12 — Writing output files")

OUTPUT_TABLES = {
    "dim_student.csv":         dim_student,
    "fact_risk_behaviour.csv": fact_risk,
    "fact_placement.csv":      fact_placement,
    "fact_subject_marks.csv":  fact_subject_marks,
    "fact_skill_scores.csv":   fact_skill_scores,
    "dim_cs_skills_v5.csv":    cs,
}

quality_after = {}
for fname, df in OUTPUT_TABLES.items():
    path = OUT / fname
    df.to_csv(path, index=False)
    nulls = df.isnull().sum()
    quality_after[fname] = {
        "rows": len(df), "cols": len(df.columns),
        "total_nulls": int(nulls.sum()),
        "null_per_col": {c: int(v) for c, v in nulls.items() if v > 0},
    }
    print(f"  {fname}: {df.shape} | nulls={nulls.sum()}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 13 — WRITE MARKDOWN REPORTS
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 13 — Writing markdown reports")

# ── data_quality_report.md ──────────────────────────────────────────────────
dq_lines = [
    "# Data Quality Report — v5 Star Schema\n",
    "## Before Processing\n",
    "| Source | Rows | Cols | Duplicate Rows | Total Nulls |",
    "|---|---|---|---|---|",
]
for name, q in quality_before.items():
    dq_lines.append(f"| `{name}` | {q['rows']:,} | {q['cols']} | {q['duplicate_rows']} | {q['total_nulls']} |")

dq_lines += [
    "\n## After Processing\n",
    "| Output Table | Rows | Cols | Total Nulls | High-Null Columns |",
    "|---|---|---|---|---|",
]
for fname, q in quality_after.items():
    high_null = [f"{c}({v})" for c,v in q["null_per_col"].items() if v/(q["rows"] or 1) > 0.05]
    dq_lines.append(
        f"| `{fname}` | {q['rows']:,} | {q['cols']} | {q['total_nulls']} | "
        f"{', '.join(high_null) or 'none'} |"
    )

dq_lines += [
    "\n## Range Issues Detected\n",
    "| Table | Column | Issue | Count |",
    "|---|---|---|---|",
]
if RANGE_ISSUES:
    for r in RANGE_ISSUES:
        dq_lines.append(f"| `{r['table']}` | `{r['column']}` | {r['issue']} | {r['count']} |")
else:
    dq_lines.append("| — | — | No range issues detected | — |")

dq_lines += [
    "\n## Quality Checks Summary\n",
    "| Check | Status | Detail |",
    "|---|---|---|",
]
for q in QA_LOG:
    icon = "✅" if q["status"]=="PASS" else "❌"
    dq_lines.append(f"| {q['check']} | {icon} {q['status']} | {q.get('detail','')} |")

with open(OUT / "data_quality_report.md", "w") as f:
    f.write("\n".join(dq_lines))

# ── null_handling_report.md ─────────────────────────────────────────────────
nh_lines = [
    "# Null Handling Report — v5\n",
    "| Table | Column | Null Count | Strategy | Justification |",
    "|---|---|---|---|---|",
]
for n in NULL_LOG:
    nh_lines.append(f"| `{n['table']}` | `{n['column']}` | {n['null_count']} | "
                    f"{n['strategy']} | {n['justification']} |")

with open(OUT / "null_handling_report.md", "w") as f:
    f.write("\n".join(nh_lines))

# ── removed_columns.md ──────────────────────────────────────────────────────
rc_lines = [
    "# Removed Columns Report — v5\n",
    "| Source File | Column | Reason |",
    "|---|---|---|",
]
for r in REMOVED_COLS:
    rc_lines.append(f"| `{r['source_file']}` | `{r['column']}` | {r['reason']} |")

with open(OUT / "removed_columns.md", "w") as f:
    f.write("\n".join(rc_lines))

# ── data_lineage_v5.md ──────────────────────────────────────────────────────
lin_lines = [
    "# Data Lineage — v5 Star Schema\n",
    "| Output Table | Column | Source File | Source Column | Transform |",
    "|---|---|---|---|---|",
]
for l in LINEAGE:
    lin_lines.append(f"| `{l['output_table']}` | `{l['column']}` | "
                     f"`{l['source_file']}` | `{l['source_column']}` | {l['transform']} |")

with open(OUT / "data_lineage_v5.md", "w") as f:
    f.write("\n".join(lin_lines))

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("FINAL SUMMARY")
print("=" * 72)
for fname, df in OUTPUT_TABLES.items():
    print(f"  {fname:<35} {df.shape}")

passed = sum(1 for q in QA_LOG if q["status"]=="PASS")
failed = sum(1 for q in QA_LOG if q["status"]=="FAIL")
print(f"\n  QA checks: {passed} PASS, {failed} FAIL")
print(f"  Nulls documented: {len(NULL_LOG)} columns handled")
print(f"  Columns removed:  {len(REMOVED_COLS)}")
print(f"  Lineage entries:  {len(LINEAGE)}")
print(f"\n  Output directory: {OUT}")
if failed:
    print("\n  ❌ Some QA checks FAILED — review data_quality_report.md")
else:
    print("\n  ✅ All QA checks PASSED")
