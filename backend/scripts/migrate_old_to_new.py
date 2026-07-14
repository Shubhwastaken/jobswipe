"""OLD_DB -> NEW_DB data migration (Stage 9e).

Dry-run by default: the full migration executes inside ONE transaction on NEW_DB
and is rolled back unconditionally unless --execute is passed. OLD_DB is opened
read-only and is never written to. Connection strings come from backend/.env via
os.getenv and are never printed.

Column mapping is the explicit list approved in Stage 9c - no guessing.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import OrderedDict
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# -- Approved column mapping (Stage 9c). Same-name OLD -> NEW. ----------------
# students: 19 mapped columns; id/branch/college_name/skills/projects/
# certifications are deliberately excluded (junk or superseded).
STUDENTS_KEY = "student_id"
STUDENTS_COLS = [
    "student_id",
    "10th_board", "10th_marks", "12th_board", "12th_marks",
    "active_backlogs", "backlogs_history", "batch_year", "cgpa", "created_at",
    "department", "email", "full_name", "gender", "name", "password_hash",
    "portfolio_url", "register_number", "year_of_study",
]
# DO UPDATE list = mapped columns minus the conflict key. Explicitly NEVER
# touches: resume_url, resume_parse_confidence, id, branch, college_name, source.
STUDENTS_UPDATE_COLS = [c for c in STUDENTS_COLS if c != STUDENTS_KEY]

JOBS_JSONB_CASTS = {  # OLD text[] -> NEW jsonb via to_jsonb()
    "required_skills", "preferred_skills", "allowed_departments",
    "allowed_branches", "grad_years_eligible", "selection_rounds",
}

# (table, conflict_key, [columns])  in FK dependency order (9c).
TABLES: "OrderedDict[str, tuple[str, list[str]]]" = OrderedDict([
    ("students", (STUDENTS_KEY, STUDENTS_COLS)),
    ("recruiters", ("id", ["id", "company_domain", "company_name", "created_at",
                           "email", "name", "password_hash"])),
    ("companies", ("company_id", ["company_id", "allowed_departments", "bond_years",
                                  "cert_tier_required", "company_name", "industry",
                                  "internship_tier_preference", "max_active_backlogs",
                                  "min_10th", "min_12th", "min_cgpa",
                                  "min_internship_months", "min_projects", "package_lpa",
                                  "preferred_skills", "project_complexity_min",
                                  "required_skills", "requires_research_paper",
                                  "role_offered", "tier"])),
    ("jobs", ("id", ["id", "allowed_branches", "allowed_departments", "batch_year",
                     "bond_years", "careers_url", "company_name", "created_at", "ctc",
                     "grad_years_eligible", "highlight_line", "industry",
                     "interview_timeline", "is_active", "job_description", "location",
                     "max_backlogs", "mentorship", "min_cgpa", "package_lpa",
                     "preferred_skills", "recruiter_id", "remote_policy",
                     "required_skills", "role", "role_title", "selection_rounds"])),
    ("skills", ("id", ["id", "proficiency", "skill_name", "student_id", "verified"])),
    ("projects", ("project_id", ["project_id", "complexity", "domain", "duration_weeks",
                                 "has_deployment", "has_github", "project_title",
                                 "student_id", "team_size", "tech_stack", "year"])),
    ("certifications", ("cert_id", ["cert_id", "cert_name", "domain", "issuing_body",
                                    "student_id", "tier", "year_obtained"])),
    ("internships", ("internship_id", ["internship_id", "company_name", "company_tier",
                                       "domain", "duration_months", "mode", "role",
                                       "stipend", "student_id", "year"])),
    ("research_papers", ("paper_id", ["paper_id", "co_authors_count", "domain",
                                      "is_first_author", "publication_venue",
                                      "student_id", "tier", "title", "year_published"])),
    ("student_interest", ("id", ["id", "created_at", "job_id", "student_id"])),
    ("student_pass", ("id", ["id", "created_at", "job_id", "student_id"])),
    ("recruiter_interest", ("id", ["id", "created_at", "job_id", "recruiter_id",
                                   "student_id"])),
    ("recruiter_pass", ("id", ["id", "created_at", "insight_payload", "job_id",
                               "reason_code", "reason_note", "recruiter_id",
                               "student_id"])),
    ("matches", ("id", ["id", "job_id", "matched_at", "recruiter_id", "student_id"])),
    ("interview_sessions", ("id", ["id", "competency_plan", "completed_at", "created_at",
                                   "current_index", "follow_up_used", "interview_stage",
                                   "phase", "question_sequence", "self_rating",
                                   "seniority", "started_at", "status",
                                   "structured_profile", "student_id", "target_domain",
                                   "target_role"])),
    ("interview_turns", ("id", ["id", "content", "created_at", "question_ref",
                                "session_id", "speaker", "turn_index"])),
    ("interview_feedback", ("id", ["id", "created_at", "headline_takeaway",
                                   "next_session_suggestion", "overall_summary",
                                   "per_question_feedback", "recurring_patterns",
                                   "session_id"])),
    ("model_fairness_history", ("id", ["id", "accuracy", "company_id", "delta_dp",
                                       "delta_eo", "epsilon", "f1", "trained_at",
                                       "triggered_by"])),
])

# Explicitly skipped: 0 rows in OLD (verified in 9b).
SKIPPED_TABLES = ["applications", "bias_recommendations", "eligibility_results",
                  "improvement_plans", "learning_resources", "skills_graph"]

# Child tables for the post-merge orphan check (student_id -> students).
ORPHAN_CHECK_TABLES = ["skills", "projects", "certifications", "internships",
                       "research_papers", "student_interest", "student_pass",
                       "recruiter_interest", "recruiter_pass", "matches",
                       "applications", "interview_sessions"]


def get_dsn(name: str) -> str:
    val = (os.getenv(name) or "").strip()
    if not val.startswith(("postgresql://", "postgres://")):
        raise SystemExit(f"{name} missing or not a postgresql:// DSN (value not shown)")
    if "sslmode" not in val:
        val += ("&" if "?" in val else "?") + "sslmode=require"
    return val


# TCP keepalives so a quiet or flaky link doesn't silently drop the session.
KEEPALIVE_KW = dict(keepalives=1, keepalives_idle=20,
                    keepalives_interval=10, keepalives_count=5)

PAGE_SIZE = 200  # rows per batched INSERT page (keeps round trips low)


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def adapt(value, as_array: bool = False):
    """psycopg2 adaptation: dict/list from jsonb columns re-bind as Json.
    Columns going through to_jsonb(%s::text[]) must stay plain Python lists so
    psycopg2 renders a native ARRAY, not a JSON string."""
    if as_array:
        return value
    if isinstance(value, (dict, list)):
        return psycopg2.extras.Json(value)
    return value


def fetch_old_rows(old_cur, table: str, cols: list[str], jsonb_casts=frozenset()):
    """Read mapped columns from OLD. Array->jsonb cast columns are read as text[]
    (their native OLD type); the INSERT applies to_jsonb() on the NEW side."""
    col_sql = ", ".join(qident(c) for c in cols)
    old_cur.execute(f'SELECT {col_sql} FROM public.{qident(table)}')
    return old_cur.fetchall()


def build_insert_parts(table: str, key: str, cols: list[str]):
    """Return (insert_head, row_template, conflict_tail) for batched or per-row use."""
    col_sql = ", ".join(qident(c) for c in cols)
    placeholders = []
    for c in cols:
        if table == "jobs" and c in JOBS_JSONB_CASTS:
            placeholders.append("to_jsonb(%s::text[])")   # approved cast
        else:
            placeholders.append("%s")

    if table == "students":
        # OLD wins, but never nulls a NEW value: COALESCE per approved policy.
        sets = ", ".join(
            f"{qident(c)} = COALESCE(excluded.{qident(c)}, students.{qident(c)})"
            for c in STUDENTS_UPDATE_COLS
        )
        head = f'INSERT INTO public.{qident(table)} ({col_sql}, "source") VALUES %s'
        template = "(" + ", ".join(placeholders) + ", 'migrated')"
        tail = (f' ON CONFLICT ({qident(key)}) DO UPDATE SET {sets}'
                f' RETURNING (xmax = 0) AS inserted')
        return head, template, tail
    head = f'INSERT INTO public.{qident(table)} ({col_sql}) VALUES %s'
    template = "(" + ", ".join(placeholders) + ")"
    tail = f' ON CONFLICT ({qident(key)}) DO NOTHING RETURNING 1'
    return head, template, tail


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate OLD_DB data into NEW_DB.")
    parser.add_argument("--execute", action="store_true",
                        help="Actually COMMIT. Without this flag the transaction is "
                             "ALWAYS rolled back (dry run).")
    args = parser.parse_args()
    dry_run = not args.execute

    old_conn = psycopg2.connect(get_dsn("OLD_DB_URL"), connect_timeout=20, **KEEPALIVE_KW)
    old_conn.set_session(readonly=True)          # OLD_DB is read-only, enforced
    new_conn = psycopg2.connect(get_dsn("NEW_DB_URL"), connect_timeout=20, **KEEPALIVE_KW)
    new_conn.autocommit = False                  # single transaction

    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()
    report_rows = []
    failed = False

    try:
        # -- students.source backfill (before the merge) ----------------------
        new_cur.execute("UPDATE public.students SET source = 'roster' "
                        "WHERE source IS NULL")
        roster_marked = new_cur.rowcount
        print(f"source backfill: {roster_marked} existing NEW rows marked 'roster'")

        # -- per-table migration ----------------------------------------------
        for table, (key, cols) in TABLES.items():
            old_rows = fetch_old_rows(old_cur, table, cols)
            new_cur.execute(f'SELECT COUNT(*) FROM public.{qident(table)}')
            before = new_cur.fetchone()[0]

            head, template, tail = build_insert_parts(table, key, cols)
            row_sql = head.replace("VALUES %s", f"VALUES {template}") + tail
            inserted = updated = skipped = 0
            skip_reasons: dict[str, int] = {}

            def count_results(results, n_rows):
                nonlocal inserted, updated, skipped
                if table == "students":
                    ins = sum(1 for r in results if r and r[0])
                    inserted += ins
                    updated += n_rows - ins       # conflict path: DO UPDATE ran
                else:
                    inserted += len(results)
                    conflicts = n_rows - len(results)
                    if conflicts:
                        skipped += conflicts      # ON CONFLICT DO NOTHING
                        skip_reasons["pk already in NEW"] = \
                            skip_reasons.get("pk already in NEW", 0) + conflicts

            for start in range(0, len(old_rows), PAGE_SIZE):
                page = old_rows[start:start + PAGE_SIZE]
                array_flags = [table == "jobs" and c in JOBS_JSONB_CASTS for c in cols]
                params = [tuple(adapt(v, as_array=flag) for v, flag in zip(row, array_flags))
                          for row in page]
                new_cur.execute("SAVEPOINT page_sp")
                try:
                    results = psycopg2.extras.execute_values(
                        new_cur, head + tail, params, template=template,
                        page_size=len(params), fetch=True)
                except Exception:
                    new_cur.execute("ROLLBACK TO SAVEPOINT page_sp")
                    # page failed - isolate per row to capture reasons
                    for prow in params:
                        new_cur.execute("SAVEPOINT row_sp")
                        try:
                            new_cur.execute(row_sql, prow)
                            count_results(new_cur.fetchall(), 1)
                            new_cur.execute("RELEASE SAVEPOINT row_sp")
                        except Exception as exc:
                            new_cur.execute("ROLLBACK TO SAVEPOINT row_sp")
                            skipped += 1
                            reason = f"{type(exc).__name__}: {str(exc).splitlines()[0][:90]}"
                            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    continue
                # page succeeded
                new_cur.execute("RELEASE SAVEPOINT page_sp")
                count_results(results, len(params))

            projected = before + inserted
            report_rows.append((table, len(old_rows), inserted, updated, skipped,
                                before, projected, skip_reasons))

        # -- sequence reset (inside the transaction) --------------------------
        new_cur.execute(
            "SELECT setval(pg_get_serial_sequence('public.skills','id'), "
            "COALESCE((SELECT MAX(id) FROM public.skills), 1))")
        setval_result = new_cur.fetchone()[0]
        new_cur.execute("SELECT COALESCE(MAX(id), 0) FROM public.skills")
        max_id = new_cur.fetchone()[0]
        seq_ok = setval_result >= max_id
        print(f"skills_id_seq setval -> {setval_result} (MAX(id)={max_id}) "
              f"{'OK' if seq_ok else 'FAIL'}")
        if not seq_ok:
            failed = True

        # -- orphan check (post-merge state, before any rollback) -------------
        print("\n-- orphan check (child.student_id with no parent in students) --")
        for t in ORPHAN_CHECK_TABLES:
            new_cur.execute(
                f'SELECT COUNT(*) FROM public.{qident(t)} c '
                f'WHERE c.student_id IS NOT NULL AND NOT EXISTS '
                f'(SELECT 1 FROM public.students s WHERE s.student_id = c.student_id)')
            orphans = new_cur.fetchone()[0]
            status = "OK" if orphans == 0 else "ORPHANS - DRY RUN FAILED"
            print(f"  {t}: {orphans}  {status}")
            if orphans:
                failed = True

        # -- report -----------------------------------------------------------
        print("\n-- per-table report --")
        hdr = f"{'table':24} {'OLD':>6} {'insert':>7} {'update':>7} {'skip':>5} {'NEW before':>10} {'NEW after':>10}"
        print(hdr); print("-" * len(hdr))
        for t, old_n, ins, upd, skp, before, after, reasons in report_rows:
            print(f"{t:24} {old_n:>6} {ins:>7} {upd:>7} {skp:>5} {before:>10} {after:>10}")
            for r, n in reasons.items():
                print(f"{'':24}   skip reason ({n}x): {r}")
        for t in SKIPPED_TABLES:
            print(f"{t:24} {'-':>6} {'-':>7} {'-':>7} {'-':>5}   skipped: 0 rows in OLD")

        # -- commit / rollback ------------------------------------------------
        if failed:
            new_conn.rollback()
            print("\nRESULT: FAILED - transaction rolled back (orphans or sequence check).")
            return 1
        if dry_run:
            new_conn.rollback()
            print("\nRESULT: DRY RUN - transaction rolled back. Re-run with --execute to commit.")
            return 0
        new_conn.commit()
        print("\nRESULT: EXECUTED - transaction committed.")
        return 0
    except Exception:
        new_conn.rollback()
        print("\nRESULT: ERROR - transaction rolled back.", file=sys.stderr)
        raise
    finally:
        old_conn.close()
        new_conn.close()


if __name__ == "__main__":
    sys.exit(main())
