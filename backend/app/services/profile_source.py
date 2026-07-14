"""DB-backed equivalents of the three CSV profile loaders.

Stage 10c. The serving path (eligibility, TalentForge match, Fairlearn scoring)
historically read backend/data/*.csv, so a student who signed up today was
invisible to the matcher. These functions return the *same shapes* from the
students/skills/projects/certifications/internships/research_papers tables, so
the loaders in talentforge_matcher and routers.swipe can swap their source
without any caller, the matcher, the ranker, or the champion artifact changing.

Two invariants this module exists to protect:

  * ``student_feature_rows_from_db`` does NOT reimplement feature engineering.
    It calls ``build_student_features`` from src.preprocessing.feature_engineering
    — the same function that generated student_features.csv — with DB-sourced
    DataFrames carrying the CSV column names, and drops ``skill_list`` exactly as
    the CSV export does (feature_engineering.py:298). Skills reach the model only
    via load_profiles.
  * Under JOBSWIPE_DATASET=realworld the DB is unreachable regardless of
    PROFILE_SOURCE. That variant is the paper's evaluation path and must keep
    reading data/resume_realworld_normalized/.
"""

import os
from typing import Any, Dict, List

import pandas as pd

from app.config import PROFILE_SOURCE
from app.database import supabase
from app.services.data_paths import dataset_variant

# The 12 columns of students.csv, in file order. The DB students table carries
# extra serving columns (id, email, batch_year, branch, ...) that the CSV loader
# never returned; the DB loader must not return them either, or build_student_model_input's
# merge order would start seeing keys it does not see under PROFILE_SOURCE=csv.
STUDENTS_CSV_COLUMNS = [
    "student_id",
    "full_name",
    "gender",
    "department",
    "10th_marks",
    "10th_board",
    "12th_marks",
    "12th_board",
    "cgpa",
    "backlogs_history",
    "active_backlogs",
    "year_of_study",
]


def profile_source() -> str:
    """Resolve the active profile source: "csv" or "db".

    Read from the environment on every call (not cached at import) so the parity
    harness can flip it in-process. The realworld guard is absolute.
    """
    if dataset_variant() == "realworld":
        return "csv"
    return os.getenv("PROFILE_SOURCE", PROFILE_SOURCE).strip().lower()


def use_db_profiles() -> bool:
    return profile_source() == "db"


def _frame(table: str, columns: List[str], sort_by: List[str]) -> pd.DataFrame:
    """Fetch a table as a DataFrame with the CSV's column names and row order.

    ``columns`` is the CSV header for that table; an empty result still has to
    carry them, because build_student_features groups/aggregates on them by name.

    ``sort_by`` matters beyond tidiness: load_profiles keeps only head(3) of a
    student's projects and certifications, and those three feed the TF-IDF text
    the match score is computed from. SQL row order is not guaranteed, so sort
    explicitly on the same key the CSVs are ordered by (student_id, then the
    child's own id) or the DB path would silently keep a different three.
    """
    rows = supabase.table(table).select("*").order("student_id").execute().data or []
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    frame = frame.sort_values(by=sort_by, kind="stable").reset_index(drop=True)
    return frame[columns]


def students_frame() -> pd.DataFrame:
    return _frame("students", STUDENTS_CSV_COLUMNS, ["student_id"])


def skills_frame() -> pd.DataFrame:
    return _frame("skills", ["student_id", "skill_name", "proficiency", "verified"], ["student_id", "id"])


def projects_frame() -> pd.DataFrame:
    return _frame("projects", [
        "student_id", "project_id", "project_title", "domain", "tech_stack",
        "complexity", "team_size", "has_deployment", "has_github", "duration_weeks", "year",
    ], ["student_id", "project_id"])


def certifications_frame() -> pd.DataFrame:
    return _frame("certifications", [
        "student_id", "cert_id", "cert_name", "issuing_body", "tier", "domain", "year_obtained",
    ], ["student_id", "cert_id"])


def internships_frame() -> pd.DataFrame:
    return _frame("internships", [
        "student_id", "internship_id", "company_name", "company_tier", "role",
        "domain", "duration_months", "stipend", "mode", "year",
    ], ["student_id", "internship_id"])


def research_papers_frame() -> pd.DataFrame:
    return _frame("research_papers", [
        "student_id", "paper_id", "title", "publication_venue", "tier", "domain",
        "year_published", "is_first_author", "co_authors_count",
    ], ["student_id", "paper_id"])


def profiles_from_db() -> Dict[str, Dict[str, Any]]:
    """DB equivalent of talentforge_matcher.load_profiles().

    Mirrors the CSV version field for field, including its defaults (year_of_study
    falls back to 3, full_name to the student_id) and its caps (projects and
    certifications are head(3); skills and internships are uncapped).
    """
    students = students_frame()
    if students.empty:
        return {}

    skills = skills_frame()
    projects = projects_frame()
    certs = certifications_frame()
    internships = internships_frame()

    profiles: Dict[str, Dict[str, Any]] = {}
    allowed_student_ids = set(students["student_id"].astype(str))

    for _, row in students.iterrows():
        sid = str(row.get("student_id"))
        profiles[sid] = {
            "student_id": sid,
            "full_name": row.get("full_name") or sid,
            "department": row.get("department") or "",
            "cgpa": float(row.get("cgpa") or 0),
            "active_backlogs": int(row.get("active_backlogs") or 0),
            "year_of_study": int(row.get("year_of_study") or 3),
            "skills": [],
            "projects": [],
            "certifications": [],
            "internships": [],
        }

    if not skills.empty:
        skills = skills[skills["student_id"].astype(str).isin(allowed_student_ids)].copy()
        for sid, group in skills.groupby("student_id"):
            if sid in profiles:
                profiles[sid]["skills"] = group["skill_name"].dropna().astype(str).tolist()

    if not projects.empty:
        projects = projects[projects["student_id"].astype(str).isin(allowed_student_ids)].copy()
        for sid, group in projects.groupby("student_id"):
            if sid in profiles:
                profiles[sid]["projects"] = [
                    {
                        "title": item.get("project_title") or "Project",
                        "description": item.get("domain") or item.get("tech_stack") or "Applied project",
                        "tech_stack": item.get("tech_stack") or "",
                        "complexity": item.get("complexity") or "",
                    }
                    for item in group.head(3).to_dict("records")
                ]

    if not certs.empty:
        certs = certs[certs["student_id"].astype(str).isin(allowed_student_ids)].copy()
        for sid, group in certs.groupby("student_id"):
            if sid in profiles:
                profiles[sid]["certifications"] = [
                    {
                        "name": item.get("cert_name") or "Certification",
                        "issuer": item.get("issuing_body") or "Issuer",
                        "domain": item.get("domain") or "",
                        "tier": item.get("tier") or "",
                    }
                    for item in group.head(3).to_dict("records")
                ]

    if not internships.empty:
        internships = internships[internships["student_id"].astype(str).isin(allowed_student_ids)].copy()
        for sid, group in internships.groupby("student_id"):
            if sid in profiles:
                profiles[sid]["internships"] = group.to_dict("records")

    return profiles


def student_csv_rows_from_db() -> Dict[str, Dict[str, Any]]:
    """DB equivalent of swipe.load_student_csv_rows() — raw students.csv rows.

    Restricted to the 12 CSV columns, with NULL rendered as "" to match the
    ``pd.read_csv(...).fillna("")`` the CSV loader applies.
    """
    students = students_frame()
    if students.empty:
        return {}
    frame = students.fillna("")
    return {str(row["student_id"]): row for row in frame.to_dict("records") if row.get("student_id")}


def student_feature_rows_from_db() -> Dict[str, Dict[str, Any]]:
    """DB equivalent of swipe.load_student_feature_rows().

    Calls the same build_student_features() that produced student_features.csv,
    then reproduces the CSV export step (drop skill_list) and the CSV read step
    (fillna("")), so the returned rows are indistinguishable from parsed CSV rows.
    """
    from src.preprocessing.feature_engineering import build_student_features

    students = students_frame()
    if students.empty:
        return {}

    features = build_student_features(
        students,
        certifications_frame(),
        projects_frame(),
        internships_frame(),
        research_papers_frame(),
        skills_frame(),
    )
    # feature_engineering.py:298 — skill_list is dropped on export, so the CSV
    # loader never returns it and neither may we. Skills reach the model via
    # load_profiles only.
    features = features.drop(columns=["skill_list"], errors="ignore").fillna("")
    return {str(row["student_id"]): row for row in features.to_dict("records") if row.get("student_id")}
