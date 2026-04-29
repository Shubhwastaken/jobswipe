from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, validator, EmailStr
import re
import hashlib
import bcrypt
from jose import jwt
from app.database import supabase
from app.config import JWT_SECRET

router = APIRouter(prefix="/auth", tags=["auth"])
REG_PATTERN = re.compile(r"^RA\d{13}$")


class SignupRequest(BaseModel):
    name: str
    register_number: str
    email: EmailStr
    password: str

    @validator("register_number")
    def validate_reg(cls, v):
        if not REG_PATTERN.match(v):
            raise ValueError("Register number must follow pattern RA2311047010209")
        return v


class LoginRequest(BaseModel):
    register_number: str
    password: str


@router.post("/signup")
def signup(req: SignupRequest):
    existing = supabase.table("students").select("id").eq("register_number", req.register_number).maybe_single().execute()
    if existing and existing.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Register number already exists")

    # Hash password with SHA256 first, then bcrypt
    sha256_hash = hashlib.sha256(req.password.encode()).hexdigest()
    bcrypt_hash = bcrypt.hashpw(sha256_hash.encode(), bcrypt.gensalt()).decode()
    
    supabase.table("students").insert({
        "register_number": req.register_number,
        "name": req.name,
        "email": req.email,
        "password_hash": bcrypt_hash,
    }).execute()
    return {"message": "Signup successful"}


@router.post("/login")
def login(req: LoginRequest):
    result = supabase.table("students").select("*").eq("register_number", req.register_number).maybe_single().execute()
    
    if not result or not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")

    student = result.data
    # Hash password with SHA256 first, then verify with bcrypt
    sha256_hash = hashlib.sha256(req.password.encode()).hexdigest()
    stored_hash = student.get("password_hash", "")
    
    if not bcrypt.checkpw(sha256_hash.encode(), stored_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    token = jwt.encode({"sub": student["id"], "reg": req.register_number}, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "student_id": student["id"], "name": student["name"]}
