from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import supabase
from app.routers.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    branch: str
    cgpa: float
    active_backlogs: int
    batch_year: int


@router.patch("/{student_id}")
def update_profile(student_id: str, data: ProfileUpdate, user=Depends(get_current_user)):
    if user["id"] != student_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    supabase.table("students").update({
        "branch": data.branch,
        "cgpa": data.cgpa,
        "active_backlogs": data.active_backlogs,
        "batch_year": data.batch_year,
    }).eq("id", student_id).execute()
    return {"message": "Profile updated"}
