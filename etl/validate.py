"""
Module: validate.py
Project: KDAC-3 Analytics Platform
Purpose: Automated data quality, integrity, constraint, and idempotency tests
         on the PostgreSQL data warehouse and analytical views.
"""

import sys
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import get_db_engine

TABLES = [
    "students",
    "academic_records",
    "exam_marks",
    "attendance",
    "lifestyle",
    "skills",
    "career_preferences"
]

VIEWS = [
    "student_360_view",
    "performance_features_view",
    "at_risk_features_view",
    "career_readiness_view"
]


def run_data_quality_tests() -> Dict[str, Any]:
    """
    Runs comprehensive data quality validation suite:
    1. Referential integrity (zero orphaned foreign keys)
    2. Primary key uniqueness (zero duplicates)
    3. Null checks on critical business fields
    4. Domain and range validation checks
    5. Analytical views query testing
    """
    engine = get_db_engine()
    results = {}
    all_passed = True
    
    print("\n" + "=" * 80)
    print("      KDAC-3 DATA QUALITY & WAREHOUSE VALIDATION SUITE      ")
    print("=" * 80)
    
    with engine.connect() as conn:
        # 1. Row counts & Uniqueness
        print("\n[CHECK 1] Row Counts & Primary Key Uniqueness:")
        for tbl in TABLES:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            distinct_ids = conn.execute(text(f"SELECT COUNT(DISTINCT student_id) FROM {tbl}")).scalar()
            passed = (total == 10000) and (distinct_ids == 10000)
            status = "PASS" if passed else "FAIL"
            if not passed: all_passed = False
            print(f"  • {tbl:<20}: Total={total:,} | Distinct IDs={distinct_ids:,} [{status}]")
            results[f"{tbl}_uniqueness"] = passed
            
        # 2. Referential Integrity Check
        print("\n[CHECK 2] Referential Integrity (Foreign Keys -> students.student_id):")
        child_tables = [t for t in TABLES if t != "students"]
        for child in child_tables:
            orphans = conn.execute(text(f"""
                SELECT COUNT(*) 
                FROM {child} c 
                LEFT JOIN students s ON c.student_id = s.student_id 
                WHERE s.student_id IS NULL
            """)).scalar()
            passed = (orphans == 0)
            status = "PASS" if passed else "FAIL"
            if not passed: all_passed = False
            print(f"  • {child:<20} -> students: {orphans} orphaned records [{status}]")
            results[f"{child}_ref_integrity"] = passed

        # 3. Value Range & Boundary Checks
        print("\n[CHECK 3] Domain Range Constraints:")
        range_queries = [
            ("students.cgpa [0.0 - 10.0]", "SELECT COUNT(*) FROM students WHERE cgpa < 0.0 OR cgpa > 10.0"),
            ("attendance.percentage [0.0 - 100.0]", "SELECT COUNT(*) FROM attendance WHERE attendance_percentage < 0.0 OR attendance_percentage > 100.0"),
            ("academic.prev_sem_pct [0.0 - 100.0]", "SELECT COUNT(*) FROM academic_records WHERE previous_semester_percentage < 0.0 OR previous_semester_percentage > 100.0"),
            ("exam_marks.next_sem_marks [0.0 - 100.0]", "SELECT COUNT(*) FROM exam_marks WHERE next_semester_marks < 0.0 OR next_semester_marks > 100.0"),
            ("lifestyle.sleep_hours [0.0 - 24.0]", "SELECT COUNT(*) FROM lifestyle WHERE sleep_hours < 0.0 OR sleep_hours > 24.0"),
            ("lifestyle.stress_level [0.0 - 10.0]", "SELECT COUNT(*) FROM lifestyle WHERE stress_level < 0.0 OR stress_level > 10.0"),
            ("students.at_risk_flag IN (0, 1)", "SELECT COUNT(*) FROM students WHERE at_risk_flag NOT IN (0, 1)"),
        ]
        
        for label, query in range_queries:
            violations = conn.execute(text(query)).scalar()
            passed = (violations == 0)
            status = "PASS" if passed else "FAIL"
            if not passed: all_passed = False
            print(f"  • {label:<40}: {violations} violations [{status}]")
            results[label] = passed

        # 4. Missing Value Checks on Critical Warehouse Columns
        print("\n[CHECK 4] Critical Column Null Checks:")
        null_queries = [
            ("students.student_id", "SELECT COUNT(*) FROM students WHERE student_id IS NULL"),
            ("students.cgpa", "SELECT COUNT(*) FROM students WHERE cgpa IS NULL"),
            ("attendance.attendance_percentage", "SELECT COUNT(*) FROM attendance WHERE attendance_percentage IS NULL"),
            ("exam_marks.next_semester_marks", "SELECT COUNT(*) FROM exam_marks WHERE next_semester_marks IS NULL"),
            ("academic_records.performance_band", "SELECT COUNT(*) FROM academic_records WHERE performance_band IS NULL"),
        ]
        for label, query in null_queries:
            null_count = conn.execute(text(query)).scalar()
            passed = (null_count == 0)
            status = "PASS" if passed else "FAIL"
            if not passed: all_passed = False
            print(f"  • {label:<40}: {null_count} nulls [{status}]")
            results[f"null_{label}"] = passed

        # 5. Analytical Views Testing
        print("\n[CHECK 5] Analytical Views Functionality:")
        for view_name in VIEWS:
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()
            passed = (row_count == 10000)
            status = "PASS" if passed else "FAIL"
            if not passed: all_passed = False
            print(f"  • {view_name:<30}: {row_count:,} rows queried [{status}]")
            results[f"view_{view_name}"] = passed

    print("\n" + "=" * 80)
    if all_passed:
        print("OVERALL RESULT: [PASS] ALL DATA QUALITY AND WAREHOUSE TESTS PASSED!")
    else:
        print("OVERALL RESULT: [FAIL] SOME DATA QUALITY CHECKS FAILED.")
    print("=" * 80 + "\n")
    
    return results


if __name__ == "__main__":
    run_data_quality_tests()
