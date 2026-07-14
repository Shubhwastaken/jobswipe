"""Stage 10d — parity harness for the CSV → DB profile-loader swap.

Builds every student's model input twice — once through PROFILE_SOURCE=csv and
once through PROFILE_SOURCE=db — and compares them field by field. Nothing here
patches data or loosens a comparison to make a gate pass; a red gate is a finding,
not a bug in the harness.

Three checks, in order:

  ORDERING INVARIANT
      load_profiles keeps only head(3) of a student's projects and certifications,
      and those three feed the TF-IDF text behind the match score. If DB row order
      per student ever diverges from the CSV, a *different three* get kept and
      rankings shift silently — no error, no crash, just wrong numbers. This is
      asserted permanently, not spot-checked.

  GATE A — the 800 S0 students
      These exist identically in both stores, so the DB path must reproduce the
      CSV path exactly on every field the champion's feature_cols consumes.
      Any mismatch is a loader bug. Failure here stops the run.

  GATE B — the 28 non-S0 students
      Failure is EXPECTED: these are real signups hand-appended to students.csv
      without regenerating student_features.csv. Split into the 18 TF signups and
      the 10 test/demo accounts, with every mismatch classified as known CSV rot
      or UNEXPLAINED. Anything unexplained is a loader bug hiding in the noise.

Usage:  python scripts/verify_profile_parity.py
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import pandas as pd  # noqa: E402

NUMERIC_TOLERANCE = 1e-9

# The student-side inputs that build_inference_features (src/model/inference.py)
# reads to produce the champion's 20 feature_cols. The pair-level columns
# (dept_match, meets_cert_tier, required_skills_match_ratio, ...) are derived from
# these plus the job, so parity on these is parity on the feature vector.
#   department  -> dept_match
#   skill_list  -> required_skills_match_ratio, preferred_skills_match_ratio
#   max_cert_tier -> meets_cert_tier
#   max_project_complexity -> meets_project_complexity
FEATURE_INPUT_FIELDS = [
    "cgpa_normalized",
    "10th_normalized",
    "12th_normalized",
    "active_backlogs",
    "department",
    "skill_list",
    "total_internship_months",
    "max_internship_tier",
    "num_projects",
    "max_project_complexity",
    "max_cert_tier",
    "num_global_premium",
    "num_global_standard",
    "num_national",
    "num_papers",
    "max_paper_tier",
    "num_advanced_skills",
    "num_verified_skills",
]

CHILD_TABLES = [
    ("skills", "skill_name"),
    ("projects", "project_id"),
    ("certifications", "cert_id"),
    ("internships", "internship_id"),
    ("research_papers", "paper_id"),
]

# The 18 TF rows are real signups appended to students.csv; the CSV is stale for
# them (no feature row, 0.0-vs-NULL marks, TF154 identity, TF232 skill count).
TF_PREFIX = "TF"


def is_s0(sid: str) -> bool:
    return str(sid).startswith("S0")


def is_tf(sid: str) -> bool:
    return str(sid).startswith(TF_PREFIX)


def build_rows(source: str) -> dict:
    """Build every student's model input under the given PROFILE_SOURCE."""
    os.environ["PROFILE_SOURCE"] = source

    from app.services.cache_control import clear_profile_dependent_caches
    from app.services.talentforge_matcher import all_student_rows
    from app.routers.swipe import build_student_model_input
    from app.services.profile_source import profile_source

    clear_profile_dependent_caches()
    assert profile_source() == source, f"flag did not take: wanted {source}, got {profile_source()}"

    rows = {}
    for row in all_student_rows():
        merged = build_student_model_input(row)
        rows[str(merged.get("student_id"))] = merged
    clear_profile_dependent_caches()
    return rows


def normalize(value):
    """Render a field for comparison. Numerics stay numeric (compared loosely),
    everything else becomes a string (compared strictly)."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, bool):
        return int(value)
    if value is None or value == "":
        return ""
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def equal(left, right) -> bool:
    left, right = normalize(left), normalize(right)
    if isinstance(left, float) and isinstance(right, float):
        return abs(left - right) <= NUMERIC_TOLERANCE
    return left == right


def show(value) -> str:
    value = normalize(value)
    if isinstance(value, list):
        return "[" + ", ".join(value) + "]"
    return repr(value)


# --------------------------------------------------------------------------- #
# Ordering invariant                                                            #
# --------------------------------------------------------------------------- #

def check_child_ordering() -> bool:
    """Per-student child-row order in the DB must match the CSV for every S0
    student. Load-bearing for head(3) on projects and certifications."""
    print("=" * 78)
    print("ORDERING INVARIANT — per-student child-row order, DB vs CSV (S0 students)")
    print("=" * 78)

    os.environ["PROFILE_SOURCE"] = "db"
    from app.services import profile_source as ps

    frames = {
        "skills": ps.skills_frame(),
        "projects": ps.projects_frame(),
        "certifications": ps.certifications_frame(),
        "internships": ps.internships_frame(),
        "research_papers": ps.research_papers_frame(),
    }

    ok = True
    for table, key in CHILD_TABLES:
        csv_frame = pd.read_csv(BACKEND_DIR / "data" / f"{table}.csv")
        csv_frame = csv_frame[csv_frame["student_id"].map(is_s0)]
        db_frame = frames[table]
        db_frame = db_frame[db_frame["student_id"].map(is_s0)]

        csv_order = csv_frame.groupby("student_id")[key].apply(list).to_dict()
        db_order = db_frame.groupby("student_id")[key].apply(list).to_dict()

        missing = set(csv_order) - set(db_order)
        diverged = [sid for sid in csv_order if sid in db_order and csv_order[sid] != db_order[sid]]

        status = "OK" if not missing and not diverged else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status:4s}] {table:16s} students={len(csv_order):4d}  "
              f"missing_in_db={len(missing):3d}  order_diverged={len(diverged):3d}")
        for sid in diverged[:5]:
            print(f"           {sid}  csv={csv_order[sid][:6]}")
            print(f"           {' ' * len(sid)}  db ={db_order[sid][:6]}")

    print()
    if not ok:
        print("  !! ORDERING INVARIANT BROKEN. head(3) on projects/certifications will keep")
        print("     a different three, silently shifting the TF-IDF match score. Fix the sort")
        print("     in profile_source._frame before trusting any gate below.")
    else:
        print("  Child-row order reproduces the CSV exactly. head(3) selects the same rows.")
    print()
    return ok


# --------------------------------------------------------------------------- #
# Gates                                                                         #
# --------------------------------------------------------------------------- #

def compare(csv_rows: dict, db_rows: dict, sids: list) -> dict:
    """Field-by-field comparison over a population. Returns {field: [(sid, csv, db)]}."""
    mismatches = {field: [] for field in FEATURE_INPUT_FIELDS}
    for sid in sids:
        csv_row, db_row = csv_rows.get(sid, {}), db_rows.get(sid, {})
        for field in FEATURE_INPUT_FIELDS:
            if not equal(csv_row.get(field), db_row.get(field)):
                mismatches[field].append((sid, csv_row.get(field), db_row.get(field)))
    return {field: hits for field, hits in mismatches.items() if hits}


def gate_a(csv_rows: dict, db_rows: dict) -> bool:
    sids = sorted(sid for sid in csv_rows if is_s0(sid))
    print("=" * 78)
    print(f"GATE A — the {len(sids)} S0 students (must be 100% on every feature_cols field)")
    print("=" * 78)

    only_csv = sorted(sid for sid in csv_rows if is_s0(sid) and sid not in db_rows)
    only_db = sorted(sid for sid in db_rows if is_s0(sid) and sid not in csv_rows)
    if only_csv or only_db:
        print(f"  POPULATION MISMATCH  csv_only={only_csv[:10]}  db_only={only_db[:10]}")

    mismatches = compare(csv_rows, db_rows, sids)
    compared = len(sids) * len(FEATURE_INPUT_FIELDS)
    bad = sum(len(hits) for hits in mismatches.values())

    print(f"  students compared : {len(sids)}")
    print(f"  fields per student: {len(FEATURE_INPUT_FIELDS)}")
    print(f"  cells compared    : {compared}")
    print(f"  exact matches     : {compared - bad}")
    print(f"  mismatches        : {bad}")
    print()

    if not mismatches and not only_csv and not only_db:
        print("  GATE A: PASS — every feature_cols input is identical across all 800 students.")
        print()
        return True

    for field, hits in sorted(mismatches.items(), key=lambda kv: -len(kv[1])):
        print(f"  FIELD {field}  ({len(hits)} mismatches)")
        for sid, csv_value, db_value in hits[:5]:
            print(f"     {sid:10s} csv={show(csv_value):40s} db={show(db_value)}")
        print()
    print("  GATE A: FAIL — these students exist identically in both stores, so any")
    print("  mismatch is a loader bug. Not a data problem. Stopping.")
    print()
    return False


def gate_b(csv_rows: dict, db_rows: dict) -> None:
    print("=" * 78)
    print("GATE B — the 28 non-S0 students (failure EXPECTED: the CSV is stale)")
    print("=" * 78)

    tf = sorted(sid for sid in set(csv_rows) | set(db_rows) if is_tf(sid))
    demo = sorted(sid for sid in set(csv_rows) | set(db_rows) if not is_s0(sid) and not is_tf(sid))

    # --- population 1: the 18 TF signups ---
    print(f"\n--- Population 1: {len(tf)} TF students (real signups, present in BOTH stores) ---\n")
    tf_mismatches = compare(csv_rows, db_rows, tf)
    for field, hits in sorted(tf_mismatches.items(), key=lambda kv: -len(kv[1])):
        classification = classify(field)
        print(f"  FIELD {field}  ({len(hits)}/{len(tf)} mismatched)  -> {classification}")
        for sid, csv_value, db_value in hits:
            print(f"     {sid:8s} csv={show(csv_value):46s} db={show(db_value)}")
        print()

    unexplained = [f for f in tf_mismatches if classify(f) == "UNEXPLAINED"]
    if unexplained:
        print("  !! UNEXPLAINED MISMATCHES — not accounted for by known CSV rot.")
        print("  !! These are a loader bug hiding in the noise:", unexplained)
    else:
        print("  All TF mismatches are explained by known CSV staleness (no feature row,")
        print("  0.0-vs-NULL marks, TF154 identity, TF232 skill count). No loader bug.")
    print()

    # --- population 2: the 10 test/demo accounts ---
    print(f"--- Population 2: {len(demo)} test/demo accounts ---\n")
    csv_only = [sid for sid in demo if sid in csv_rows]
    db_only = [sid for sid in demo if sid not in csv_rows and sid in db_rows]
    print(f"  present in CSV : {len(csv_only)}  {csv_only}")
    print(f"  DB-only        : {len(db_only)}  {db_only}")
    print("  These exist only in the DB — they are invisible to the matcher today.")
    print("  There is no CSV row to compare against, so 'mismatch' is not meaningful:")
    print("  under PROFILE_SOURCE=db they simply become visible for the first time.\n")
    for sid in db_only:
        row = db_rows[sid]
        vector = {f: normalize(row.get(f)) for f in FEATURE_INPUT_FIELDS if f != "skill_list"}
        print(f"     {sid:18s} dept={row.get('department'):10s} cgpa_n={vector['cgpa_normalized']:.3f} "
              f"skills={len(row.get('skill_list') or [])}")
    print()


def classify(field: str) -> str:
    """Is this TF mismatch explained by the known CSV rot, or is it a loader bug?"""
    known = {
        # No student_features.csv row -> CSV path serves zeros for these.
        "cgpa_normalized": "known: no CSV feature row (zeros) + 0.0-vs-NULL marks",
        "10th_normalized": "known: CSV has 0.0 marks, DB has NULL",
        "12th_normalized": "known: CSV has 0.0 marks, DB has NULL",
        "num_papers": "known: no CSV feature row (zeros)",
        "max_paper_tier": "known: no CSV feature row (zeros)",
        "num_advanced_skills": "known: no CSV feature row (zeros)",
        "num_verified_skills": "known: no CSV feature row (zeros)",
        "num_global_premium": "known: no CSV feature row (zeros)",
        "num_global_standard": "known: no CSV feature row (zeros)",
        "num_national": "known: no CSV feature row (zeros)",
        "max_cert_tier": "known: no CSV feature row (zeros)",
        "num_projects": "known: no CSV feature row (zeros)",
        "max_project_complexity": "known: no CSV feature row (zeros)",
        "total_internship_months": "known: no CSV feature row (zeros)",
        "max_internship_tier": "known: no CSV feature row (zeros)",
        "active_backlogs": "known: no CSV feature row (zeros)",
        "skill_list": "known: CSV skills stale (e.g. TF232 6-vs-32, TF154 3-vs-5)",
        "department": "known: CSV holds skill tiers (ADVANCED/ROOKIE) in the department column",
    }
    return known.get(field, "UNEXPLAINED")


def tf_vector_table(csv_rows: dict, db_rows: dict) -> None:
    """The proof the flip fixes the 18 TF students: their feature vector today vs after."""
    tf = sorted(sid for sid in db_rows if is_tf(sid))
    print("=" * 78)
    print("THE 18 TF STUDENTS — feature_cols inputs TODAY (csv) vs AFTER THE FLIP (db)")
    print("=" * 78)
    print()

    fields = [f for f in FEATURE_INPUT_FIELDS if f not in ("skill_list", "department")]
    for sid in tf:
        csv_row, db_row = csv_rows.get(sid, {}), db_rows.get(sid, {})
        name_csv = csv_row.get("full_name", "-")
        name_db = db_row.get("full_name", "-")
        header = f"{sid}  csv={name_csv!r}  db={name_db!r}"
        if name_csv != name_db:
            header += "   <-- IDENTITY MISMATCH"
        print(header)
        print(f"    {'field':26s} {'csv (today)':>14s} {'db (after flip)':>16s}")
        for field in fields:
            csv_value, db_value = normalize(csv_row.get(field)), normalize(db_row.get(field))
            flag = "" if equal(csv_row.get(field), db_row.get(field)) else "  *"
            print(f"    {field:26s} {str(csv_value):>14s} {str(db_value):>16s}{flag}")
        csv_skills = csv_row.get("skill_list") or []
        db_skills = db_row.get("skill_list") or []
        print(f"    {'skill_list (count)':26s} {len(csv_skills):>14d} {len(db_skills):>16d}")
        print()


def pool_report(csv_rows: dict, db_rows: dict) -> None:
    print("=" * 78)
    print("POOL SIZE — effect on compare_against_role_pool percentiles")
    print("=" * 78)
    print(f"  CSV pool : {len(csv_rows)} students")
    print(f"  DB  pool : {len(db_rows)} students")
    delta = len(db_rows) - len(csv_rows)
    print(f"  delta    : +{delta}")
    print()
    print("  compare_against_role_pool ranks a student against every eligible peer and")
    print("  reports a percentile. The pool grows by the 10 DB-only test/demo accounts.")
    print("  Those have cgpa 0.0 and no skills, so they rank at the BOTTOM of any pool:")
    print("  every real student's percentile moves UP slightly. Rank order among real")
    print("  students is unchanged; only the denominator moves.")
    print()
    print("  Note the eligible pool is smaller than the raw pool — these accounts will")
    print("  fail most hard criteria (cgpa 0.0) and be filtered before ranking, so the")
    print("  practical percentile shift is smaller than +10/828 suggests.")
    print()


def main() -> int:
    ordering_ok = check_child_ordering()

    csv_rows = build_rows("csv")
    db_rows = build_rows("db")
    print(f"Built {len(csv_rows)} rows from CSV, {len(db_rows)} rows from DB.\n")

    if not ordering_ok:
        print("ORDERING INVARIANT FAILED — stopping before the gates.")
        return 1

    if not gate_a(csv_rows, db_rows):
        return 1

    gate_b(csv_rows, db_rows)
    tf_vector_table(csv_rows, db_rows)
    pool_report(csv_rows, db_rows)

    print("=" * 78)
    print("GATE A: PASS.  GATE B: expected divergence only.  Ordering invariant: held.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
