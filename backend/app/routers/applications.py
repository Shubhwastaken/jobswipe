from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase
from app.routers.deps import get_current_user

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/apply/{student_id}/{job_id}")
def apply_to_job(student_id: str, job_id: str, user=Depends(get_current_user)):
    if user["id"] != student_id:
        raise HTTPException(status_code=403, detail="You can only apply for yourself")

    existing = supabase.table("applications").select("*").eq("student_id", student_id).eq("job_id", job_id).maybe_single().execute()
    if existing and existing.data:
        raise HTTPException(status_code=400, detail="Already applied")

    supabase.table("applications").insert({"student_id": student_id, "job_id": job_id}).execute()
    return {"message": "Applied successfully"}


@router.delete("/unapply/{student_id}/{job_id}")
def unapply_from_job(student_id: str, job_id: str, user=Depends(get_current_user)):
    """Withdraw an application from a job."""
    if user["id"] != student_id:
        raise HTTPException(status_code=403, detail="You can only unapply for yourself")

    # Find the application
    application_result = supabase.table("applications").select("*").eq("student_id", student_id).eq("job_id", job_id).maybe_single().execute()
    
    if not application_result or not application_result.data:
        raise HTTPException(status_code=404, detail="No application found for this job")
    
    app = application_result.data
    app_id = app.get("id")
    
    # Can only unapply if status is 'Applied' or 'Pending' (not in interview/final stage)
    current_status = app.get("current_status", "Applied")
    if current_status not in ["Applied", "Pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot unapply - application status is {current_status}")
    
    # Delete the application
    delete_result = supabase.table("applications").delete().eq("id", app_id).execute()
    
    return {"message": "Application withdrawn successfully", "deleted": True}


@router.get("/mine/{student_id}")
def get_my_applications(student_id: str, user=Depends(get_current_user)):
    if user["id"] != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return supabase.table("applications").select("*,jobs(*)").eq("student_id", student_id).execute().data


@router.post("/rounds/{application_id}")
def update_round(application_id: str, payload: dict, user=Depends(get_current_user)):
    # placeholder — add admin role checks
    supabase.table("applications").update({"round_results": payload}).eq("id", application_id).execute()
    return {"message": "Updated"}
