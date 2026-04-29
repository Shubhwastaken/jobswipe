from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.services.resume_parser import load_known_skills, extract_text_from_pdf, parse_resume
from app.database import supabase
from app.routers.deps import get_current_user

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload/{student_id}")
async def upload_resume(student_id: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    if user["id"] != student_id:
        raise HTTPException(status_code=403, detail="You can only upload resume for yourself")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF resumes are allowed")

    contents = await file.read()
    path = f"resumes/{student_id}.pdf"
    storage = supabase.storage.from_("resumes")
    
    # Delete old resume if it exists
    try:
        storage.remove([path])
    except Exception:
        pass  # File doesn't exist, that's fine
    
    # Upload new resume
    storage.upload(path, contents, {"content-type": "application/pdf"})
    public_url_resp = storage.get_public_url(path)

    if isinstance(public_url_resp, dict):
        public_url = public_url_resp.get("publicURL") or public_url_resp.get("public_url") or public_url_resp.get("url")
    elif isinstance(public_url_resp, str):
        public_url = public_url_resp
    else:
        public_url = None

    known_skills = load_known_skills(supabase)
    try:
        text = extract_text_from_pdf(contents)
    except Exception as e:
        print(f"Resume text extraction failed, falling back: {e}")
        text = ""

    parsed = parse_resume(text, known_skills)

    update_payload = {
        "skills": parsed["skills"],
        "projects": parsed["projects"],
    }
    if public_url:
        update_payload["resume_url"] = public_url

    supabase.table("students").update(update_payload).eq("id", student_id).execute()

    return {"skills_found": parsed["skills"], "projects": parsed["projects"], "resume_url": public_url or ""}
