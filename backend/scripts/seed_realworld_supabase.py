"""
Upload the isolated real-world resume dataset into separate Supabase tables.

Run the Supabase migration first:
  supabase/migrations/20260514_realworld_resume_dataset.sql
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import supabase

DATA_DIR = BACKEND_DIR / "data" / "resume_realworld_normalized"
PARSED_DIR = BACKEND_DIR / "data" / "resume_realworld_parsed"
MODEL_DIR = BACKEND_DIR / "models"

TABLES = {
    "students.csv": ("realworld_students", "student_id"),
    "skills.csv": ("realworld_skills", None),
    "certifications.csv": ("realworld_certifications", "cert_id"),
    "projects.csv": ("realworld_projects", "project_id"),
    "internships.csv": ("realworld_internships", "internship_id"),
    "research_papers.csv": ("realworld_research_papers", "paper_id"),
    "companies.csv": ("realworld_companies", "company_id"),
}


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in record.items():
        if pd.isna(value):
            cleaned[key] = None
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned


def chunks(records: List[Dict[str, Any]], size: int = 500):
    for index in range(0, len(records), size):
        yield records[index:index + size]


def upsert_csv(filename: str, table: str, conflict_key: str | None) -> int:
    frame = pd.read_csv(DATA_DIR / filename)
    records = [clean_record(row) for row in frame.to_dict("records")]
    if not records:
        return 0
    for batch in chunks(records):
        query = supabase.table(table).upsert(batch, on_conflict=conflict_key) if conflict_key else supabase.table(table).insert(batch)
        query.execute()
    return len(records)


def upload_model_run() -> None:
    parser_metrics_path = PARSED_DIR / "parser_robustness_metrics.json"
    training_summary_path = MODEL_DIR / "resume_realworld_training_summary.json"
    parser_metrics = json.loads(parser_metrics_path.read_text(encoding="utf-8")) if parser_metrics_path.exists() else {}
    model_metrics = json.loads(training_summary_path.read_text(encoding="utf-8")) if training_summary_path.exists() else {}
    supabase.table("realworld_model_runs").insert({
        "dataset_name": "resume_realworld",
        "artifact_prefix": "resume_realworld",
        "parser_metrics": parser_metrics,
        "model_metrics": model_metrics,
    }).execute()


def main() -> None:
    counts = {}
    for filename, (table, conflict_key) in TABLES.items():
        counts[table] = upsert_csv(filename, table, conflict_key)
    upload_model_run()
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
