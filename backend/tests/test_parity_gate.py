"""Gate A + the child-ordering invariant, promoted from scripts/verify_profile_parity.py
into CI. Stage 10 proved the DB profile loader reproduces the frozen CSV loader
exactly (14,400/14,400 cells across the 800 S0 students). This locks that in:

  * Gate A must stay at zero mismatches on every champion feature_cols input.
  * Per-student child-row order (skills/projects/certifications/internships/papers)
    must match the CSV — load_profiles keeps head(3) of projects and certs, and
    those feed the TF-IDF text behind the match score, so a reordered child table
    silently shifts scores.

Skips (never fails) when the DB is unreachable.
"""

from tests.conftest import requires_db


@requires_db
def test_child_row_ordering_invariant():
    from scripts.verify_profile_parity import check_child_ordering

    assert check_child_ordering() is True, (
        "DB child-row order diverged from the CSV; head(3) on projects/certs would "
        "keep a different three and shift the match score."
    )


@requires_db
def test_gate_a_feature_parity_is_exact():
    from scripts.verify_profile_parity import build_rows, compare, is_s0, FEATURE_INPUT_FIELDS

    csv_rows = build_rows("csv")
    db_rows = build_rows("db")

    s0 = sorted(sid for sid in csv_rows if is_s0(sid))
    assert s0, "no S0 students built from the CSV loader"

    only_csv = [sid for sid in s0 if sid not in db_rows]
    assert not only_csv, f"S0 students missing from the DB loader: {only_csv[:10]}"

    mismatches = compare(csv_rows, db_rows, s0)
    total_bad = sum(len(hits) for hits in mismatches.values())
    detail = {field: len(hits) for field, hits in mismatches.items()}
    assert total_bad == 0, (
        f"Gate A broke: {total_bad} mismatched cells across "
        f"{len(s0)} S0 students x {len(FEATURE_INPUT_FIELDS)} fields. By field: {detail}"
    )
