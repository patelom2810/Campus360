"""
Module: stitch.py
Description: Implements Steps 3-5 of the data stitching architecture:
- STEP 3: Establishes shambhuraje_placement_career_2026_clean.csv as the anchor table,
  assigning synthetic student_ids STU00001 through STU25000 in row order.
- STEP 4: Performs attribute-based similarity matching for the other 5 datasets:
  * Bucketing on performance metrics (tertiles: Low, Medium, High)
  * Bucketing on demographics (gender, branch clusters)
  * Random assignment without replacement within matching buckets
  * Preservation of statistical relationships (e.g. strong CGPA / marks correlation)
- STEP 5: Merges all datasets into a single wide table with prefixed column tags
  and saves to data/processed/student_master_wide.csv.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

INTERIM_DATA_DIR = BASE_DIR / "data" / "interim"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


def map_branch_cluster(branch_str: str) -> str:
    """Classifies degree/branch into high-level clusters for cross-table similarity matching."""
    b = str(branch_str).upper()
    if any(k in b for k in ["CS", "COMPUTER", "IT", "INFORMATION", "AI", "DS", "DATA", "SOFTWARE"]):
        return "Tech"
    elif any(k in b for k in ["MECH", "CIVIL", "ELEC", "EEE", "ECE", "ELECTRONIC", "AERO", "AUTO"]):
        return "Core_Engineering"
    else:
        return "General"


def match_source_to_anchor(
    anchor_df: pd.DataFrame,
    source_df: pd.DataFrame,
    source_perf_col: str,
    demo_cols: Optional[List[str]] = None,
    source_branch_col: Optional[str] = None,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Attribute-based matching without replacement:
    Matches rows from a smaller source dataset to anchor students based on:
    1. Performance band (Low, Medium, High)
    2. Demographic attributes (gender, branch cluster) where available.
    Guarantees at most 1 source row per anchor student.
    """
    rng = np.random.RandomState(random_state)
    s_df = source_df.copy()

    # Performance tertiles
    s_df["perf_band"] = pd.qcut(s_df[source_perf_col], q=3, labels=["Low", "Medium", "High"], duplicates="drop")
    
    if source_branch_col and source_branch_col in s_df.columns:
        s_df["branch_cluster"] = s_df[source_branch_col].apply(map_branch_cluster)

    assigned_ids = [None] * len(s_df)
    used_anchor_ids = set()

    for p_band in ["Low", "Medium", "High"]:
        anchor_band_mask = (anchor_df["perf_band"] == p_band)
        source_band_mask = (s_df["perf_band"] == p_band)

        # Build composite sub-match keys if demographic columns exist
        group_cols = []
        if demo_cols:
            for c in demo_cols:
                if c in s_df.columns and c in anchor_df.columns:
                    group_cols.append(c)

        if group_cols:
            for demo_val, s_sub in s_df[source_band_mask].groupby(group_cols, observed=False):
                vals = demo_val if isinstance(demo_val, tuple) else (demo_val,)
                cond = anchor_band_mask.copy()
                for col, val in zip(group_cols, vals):
                    cond = cond & (anchor_df[col] == val)

                avail_anchor = [sid for sid in anchor_df.loc[cond, "student_id"] if sid not in used_anchor_ids]
                n_match = min(len(avail_anchor), len(s_sub))
                if n_match > 0:
                    chosen = rng.choice(avail_anchor, size=n_match, replace=False)
                    for idx, aid in zip(s_sub.index[:n_match], chosen):
                        assigned_ids[idx] = aid
                        used_anchor_ids.add(aid)

        # Pass 2: Fallback within the exact same performance band for any remaining records
        unassigned_indices = [idx for idx in s_df[source_band_mask].index if assigned_ids[idx] is None]
        if unassigned_indices:
            avail_anchor = [sid for sid in anchor_df.loc[anchor_band_mask, "student_id"] if sid not in used_anchor_ids]
            n_match = min(len(avail_anchor), len(unassigned_indices))
            if n_match > 0:
                chosen = rng.choice(avail_anchor, size=n_match, replace=False)
                for idx, aid in zip(unassigned_indices[:n_match], chosen):
                    assigned_ids[idx] = aid
                    used_anchor_ids.add(aid)

    s_df["student_id"] = assigned_ids
    # Drop temporary grouping columns
    s_df = s_df.drop(columns=["perf_band", "branch_cluster"], errors="ignore")
    return s_df


def stitch_datasets() -> pd.DataFrame:
    """Executes Steps 3, 4, and 5 to create student_master_wide.csv."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("DATA STITCHING PIPELINE: ATTRIBUTE-BASED MATCHING")
    print("=" * 80)

    # STEP 3: Load anchor and assign synthetic student_id
    anchor_clean_path = INTERIM_DATA_DIR / "shambhuraje_clean.csv"
    if not anchor_clean_path.exists():
        raise FileNotFoundError(f"Missing anchor table: {anchor_clean_path}")

    anchor_df = pd.read_csv(anchor_clean_path)
    # Master student IDs: STU00001 through STU25000
    anchor_df["student_id"] = [f"STU{i+1:05d}" for i in range(len(anchor_df))]
    anchor_df["perf_band"] = pd.qcut(anchor_df["cgpa"], q=3, labels=["Low", "Medium", "High"], duplicates="drop")
    anchor_df["branch_cluster"] = anchor_df["branch"].apply(map_branch_cluster)

    print(f"Anchor Table Initialised: {len(anchor_df):,} students (STU00001 to STU{len(anchor_df):05d})")

    # STEP 4: Attribute-based matching for each secondary dataset
    # 1. Suvidya
    suvidya_df = pd.read_csv(INTERIM_DATA_DIR / "suvidya_clean.csv")
    if "student_id" in suvidya_df.columns:
        suvidya_df = suvidya_df.drop(columns=["student_id"])
    suvidya_matched = match_source_to_anchor(
        anchor_df=anchor_df,
        source_df=suvidya_df,
        source_perf_col="final_percentage",
        demo_cols=["gender"],
        random_state=42
    )
    print(f"  - Suvidya Matched: {suvidya_matched['student_id'].notnull().sum():,} / {len(suvidya_df):,} rows")

    # 2. Kundan
    kundan_df = pd.read_csv(INTERIM_DATA_DIR / "kundan_clean.csv")
    if "student_id" in kundan_df.columns:
        kundan_df = kundan_df.drop(columns=["student_id"])
    kundan_matched = match_source_to_anchor(
        anchor_df=anchor_df,
        source_df=kundan_df,
        source_perf_col="overall_score",
        demo_cols=["gender"],
        random_state=101
    )
    print(f"  - Kundan Matched: {kundan_matched['student_id'].notnull().sum():,} / {len(kundan_df):,} rows")

    # 3. Sehaj
    sehaj_df = pd.read_csv(INTERIM_DATA_DIR / "sehaj_clean.csv")
    if "student_id" in sehaj_df.columns:
        sehaj_df = sehaj_df.drop(columns=["student_id"])
    sehaj_matched = match_source_to_anchor(
        anchor_df=anchor_df,
        source_df=sehaj_df,
        source_perf_col="gpa",
        demo_cols=None,
        random_state=202
    )
    print(f"  - Sehaj Matched: {sehaj_matched['student_id'].notnull().sum():,} / {len(sehaj_df):,} rows")

    # 4. Navinpatidar
    navin_df = pd.read_csv(INTERIM_DATA_DIR / "navinpatidar_clean.csv")
    navin_matched = match_source_to_anchor(
        anchor_df=anchor_df,
        source_df=navin_df,
        source_perf_col="salary_inr",
        demo_cols=["branch_cluster"],
        source_branch_col="branch",
        random_state=303
    )
    print(f"  - Navinpatidar Matched: {navin_matched['student_id'].notnull().sum():,} / {len(navin_df):,} rows")

    # 5. Sakharebharat
    sakhare_df = pd.read_csv(INTERIM_DATA_DIR / "sakharebharat_clean.csv")
    if "student_id" in sakhare_df.columns:
        sakhare_df = sakhare_df.drop(columns=["student_id"])
    sakhare_matched = match_source_to_anchor(
        anchor_df=anchor_df,
        source_df=sakhare_df,
        source_perf_col="cgpa",
        demo_cols=["gender", "branch_cluster"],
        source_branch_col="branch",
        random_state=404
    )
    print(f"  - Sakharebharat Matched: {sakhare_matched['student_id'].notnull().sum():,} / {len(sakhare_df):,} rows")

    # STEP 5: Merge into a single wide table with prefixed column tags
    anchor_base = anchor_df.drop(columns=["perf_band", "branch_cluster"]).copy()
    
    # Prefix columns
    anchor_renamed = {}
    for c in anchor_base.columns:
        if c != "student_id":
            anchor_renamed[c] = f"anchor_{c}"
    wide_df = anchor_base.rename(columns=anchor_renamed)

    def prefix_dataframe(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        clean_df = df[df["student_id"].notnull()].copy()
        renamed = {}
        for c in clean_df.columns:
            if c != "student_id":
                renamed[c] = f"{prefix}_{c}"
        return clean_df.rename(columns=renamed)

    # Left-join each matched source onto the anchor table
    sources_to_join = [
        (suvidya_matched, "suvidya", "has_suvidya_match"),
        (kundan_matched, "kundan", "has_kundan_match"),
        (sehaj_matched, "sehaj", "has_sehaj_match"),
        (navin_matched, "navin", "has_navin_match"),
        (sakhare_matched, "sakhare", "has_sakhare_match")
    ]

    for matched_df, prefix, flag_col in sources_to_join:
        p_df = prefix_dataframe(matched_df, prefix)
        wide_df = wide_df.merge(p_df, on="student_id", how="left")
        first_non_id_col = [c for c in p_df.columns if c != "student_id"][0]
        wide_df[flag_col] = wide_df[first_non_id_col].notnull().astype(int)

    # Move student_id to position 0
    cols = ["student_id"] + [c for c in wide_df.columns if c != "student_id"]
    wide_df = wide_df[cols]

    # Save to data/processed/student_master_wide.csv
    out_wide_path = PROCESSED_DATA_DIR / "student_master_wide.csv"
    wide_df.to_csv(out_wide_path, index=False)

    print("-" * 80)
    print(f"WIDE TABLE GENERATED:")
    print(f"  File: {out_wide_path.name}")
    print(f"  Shape: {wide_df.shape[0]:,} rows x {wide_df.shape[1]} columns")
    print(f"  Coverage: Suvidya={wide_df['has_suvidya_match'].sum():,}, "
          f"Kundan={wide_df['has_kundan_match'].sum():,}, "
          f"Sehaj={wide_df['has_sehaj_match'].sum():,}, "
          f"Navin={wide_df['has_navin_match'].sum():,}, "
          f"Sakhare={wide_df['has_sakhare_match'].sum():,}")
    print("=" * 80 + "\n")

    return wide_df


def main():
    stitch_datasets()


if __name__ == "__main__":
    main()
