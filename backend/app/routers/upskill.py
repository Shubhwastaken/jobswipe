from fastapi import APIRouter, HTTPException, Depends
from app.database import supabase
from app.services.roadmap import generate_roadmap
from app.services.skill_normalizer import normalize_skill_set
from app.routers.deps import get_current_user

router = APIRouter(prefix="/upskill", tags=["upskill"])


@router.get("/{student_id}/{job_id}")
def get_upskill_plan(student_id: str, job_id: str, user=Depends(get_current_user)):
    # user may have student_id or id depending on the DB record
    user_sid = str(user.get("student_id") or user.get("id") or user.get("register_number") or "")
    if user_sid != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    student_result = supabase.table("students").select("*").eq("student_id", student_id).maybe_single().execute()
    student = student_result.data if student_result else None

    job_result = supabase.table("jobs").select("*").eq("id", job_id).maybe_single().execute()
    job = job_result.data if job_result else None

    if not student or not job:
        raise HTTPException(status_code=404, detail="Student or job not found")

    # A student's skills live in the normalized `skills` child table — the same
    # source resume_builder._fetch_data reads. The legacy students.skills text[]
    # column is NULL for every migrated student, so reading it made the roadmap
    # treat everyone as having zero skills and flag the whole job requirement list
    # as missing. Normalize both sides through skill_normalizer so synonyms
    # (js/javascript, ml/machine learning) match instead of showing up as gaps.
    skill_rows = (
        supabase.table("skills")
        .select("skill_name, proficiency, verified")
        .eq("student_id", student_id)
        .execute()
        .data
        or []
    )
    student["skills"] = sorted(normalize_skill_set(row.get("skill_name") for row in skill_rows))
    job["required_skills"] = sorted(normalize_skill_set(job.get("required_skills") or []))
    job["preferred_skills"] = sorted(normalize_skill_set(job.get("preferred_skills") or []))

    roadmap = generate_roadmap(student, job, supabase)
    return roadmap
