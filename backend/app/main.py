"""
FastAPI Main Application for Bias-Free AI Placement System.
Provides REST endpoints for eligibility checking, company management,
and improvement plans.
"""

import os
import sys
import json
import pandas as pd
import math
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


# Add backend root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.preprocessing.feature_engineering import (
    load_all_data, build_student_features, compute_skill_match
)
from src.explainability.criteria_checker import check_criteria
from src.explainability.explanation_generator import generate_explanation, generate_detailed_report
from src.explainability.improvement_planner import generate_improvement_plan

# Try to load model (may not be trained yet)
try:
    from src.model.inference import load_model, run_inference, build_inference_features
    model, scaler, feature_cols = load_model()
    MODEL_LOADED = True
except Exception as e:
    print(f"Warning: Model not loaded: {e}")
    MODEL_LOADED = False
    model, scaler, feature_cols = None, None, None

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

app = FastAPI(
    title="Bias-Free AI Placement System",
    description="Criteria-driven, transparent placement eligibility assessment",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Load data at startup ----------
students_df = None
companies_df = None
student_features_df = None


def load_data():
    global students_df, companies_df, student_features_df
    try:
        students_raw, certs, projects, internships, papers, skills, companies = load_all_data()
        students_df = students_raw
        companies_df = companies
        student_features_df = build_student_features(
            students_raw, certs, projects, internships, papers, skills
        )
        print(f"Loaded {len(students_df)} students, {len(companies_df)} companies")
    except Exception as e:
        print(f"Error loading data: {e}")


load_data()


# ---------- Pydantic Models ----------
class EligibilityRequest(BaseModel):
    student_id: str
    company_id: str


class BatchEligibilityRequest(BaseModel):
    company_id: str
    student_ids: Optional[List[str]] = None  # None = check all students


class CompanyCreate(BaseModel):
    company_name: str
    industry: str = "Tech"
    tier: str = "Tier2"
    min_cgpa: float = 6.0
    min_10th: float = 60.0
    min_12th: float = 60.0
    max_active_backlogs: int = 0
    allowed_departments: str = "CSE,IT,AIML,AIDS"
    required_skills: str = "Python"
    preferred_skills: str = ""
    min_internship_months: float = 0
    internship_tier_preference: str = "Any"
    min_projects: int = 0
    project_complexity_min: str = "Basic"
    requires_research_paper: bool = False
    cert_tier_required: str = "None"
    role_offered: str = "SDE"
    package_lpa: float = 5.0
    bond_years: int = 0


# ---------- API Endpoints ----------

@app.get("/")
async def root():
    return {
        "name": "Bias-Free AI Placement System",
        "version": "1.0.0",
        "model_loaded": MODEL_LOADED,
        "students_count": len(students_df) if students_df is not None else 0,
        "companies_count": len(companies_df) if companies_df is not None else 0,
    }


@app.get("/api/students")
async def get_students(
    department: Optional[str] = None,
    min_cgpa: Optional[float] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
):
    """Get students with optional filtering."""
    if students_df is None:
        raise HTTPException(500, "Data not loaded")

    df = students_df.copy()
    if department:
        df = df[df["department"] == department]
    if min_cgpa:
        df = df[df["cgpa"] >= min_cgpa]

    total = len(df)
    df = df.iloc[offset:offset + limit]

    # Don't expose gender in API responses (bias prevention)
    columns_to_return = [c for c in df.columns if c not in ["gender"]]
    records = df[columns_to_return].to_dict(orient="records")

    return {"total": total, "students": clean_nan(records)}


@app.get("/api/students/{student_id}")
async def get_student(student_id: str):
    """Get a single student's full profile."""
    if students_df is None:
        raise HTTPException(500, "Data not loaded")

    student = students_df[students_df["student_id"] == student_id]
    if student.empty:
        raise HTTPException(404, f"Student {student_id} not found")

    record = student.iloc[0].to_dict()

    # Add aggregated features if available
    if student_features_df is not None:
        features = student_features_df[student_features_df["student_id"] == student_id]
        if not features.empty:
            feat_dict = features.iloc[0].to_dict()
            # Remove skill_list (not JSON serializable directly)
            skill_list = feat_dict.pop("skill_list", [])
            record["features"] = feat_dict
            record["skill_list"] = skill_list

    return clean_nan(record)


@app.get("/api/companies")
async def get_companies(
    tier: Optional[str] = None,
    industry: Optional[str] = None,
):
    """Get all companies with optional filtering."""
    if companies_df is None:
        raise HTTPException(500, "Data not loaded")

    df = companies_df.copy()
    if tier:
        df = df[df["tier"] == tier]
    if industry:
        df = df[df["industry"] == industry]

    return {"total": len(df), "companies": clean_nan(df.to_dict(orient="records"))}


@app.get("/api/companies/{company_id}")
async def get_company(company_id: str):
    """Get a single company's requirements."""
    if companies_df is None:
        raise HTTPException(500, "Data not loaded")

    company = companies_df[companies_df["company_id"] == company_id]
    if company.empty:
        raise HTTPException(404, f"Company {company_id} not found")

    return clean_nan(company.iloc[0].to_dict())


@app.post("/api/eligibility/check")
async def check_eligibility(request: EligibilityRequest):
    """Check eligibility of a student for a company."""
    if students_df is None or companies_df is None:
        raise HTTPException(500, "Data not loaded")

    student_feat = student_features_df[
        student_features_df["student_id"] == request.student_id
    ]
    if student_feat.empty:
        raise HTTPException(404, f"Student {request.student_id} not found")

    company = companies_df[companies_df["company_id"] == request.company_id]
    if company.empty:
        raise HTTPException(404, f"Company {request.company_id} not found")

    student_data = student_feat.iloc[0].to_dict()
    company_data = company.iloc[0].to_dict()
    student_skills = student_data.get("skill_list", [])

    # Also get raw student data for criteria checker
    raw_student = students_df[students_df["student_id"] == request.student_id].iloc[0].to_dict()
    student_data.update(raw_student)

    # Run criteria check
    scorecard = check_criteria(student_data, company_data, student_skills)
    explanation = generate_explanation(scorecard, company_data.get("company_name", ""))

    # Run ML model if available
    ml_result = None
    if MODEL_LOADED:
        try:
            result = run_inference(student_data, company_data, model, scaler, feature_cols)
            ml_result = {
                "eligible": result["eligible"],
                "score": result["score"],
                "message": result["message"],
            }
        except Exception as e:
            ml_result = {"error": str(e)}

    # Generate improvement plan if not eligible
    improvement = None
    summary = scorecard.get("_summary", {})
    if not summary.get("eligible", False):
        improvement = generate_improvement_plan(
            scorecard, company_data.get("company_name", ""), company_data
        )

    # Build response (serialize scorecard)
    safe_scorecard = {}
    for key, val in scorecard.items():
        if key == "_summary":
            safe_scorecard[key] = val
        else:
            safe_scorecard[key] = {
                "passed": val.get("passed"),
                "message": val.get("message", ""),
                "is_hard": val.get("is_hard", False),
            }

    return {
        "student_id": request.student_id,
        "company_id": request.company_id,
        "criteria_eligible": summary.get("eligible", False),
        "ml_result": ml_result,
        "scorecard": safe_scorecard,
        "explanation": explanation,
        "improvement_plan": improvement,
    }


@app.post("/api/eligibility/batch")
async def batch_check_eligibility(request: BatchEligibilityRequest):
    """Check eligibility of multiple students for a company."""
    if students_df is None or companies_df is None:
        raise HTTPException(500, "Data not loaded")

    company = companies_df[companies_df["company_id"] == request.company_id]
    if company.empty:
        raise HTTPException(404, f"Company {request.company_id} not found")

    company_data = company.iloc[0].to_dict()

    if request.student_ids:
        student_ids = request.student_ids
    else:
        student_ids = students_df["student_id"].tolist()

    results = []
    for sid in student_ids:
        student_feat = student_features_df[student_features_df["student_id"] == sid]
        if student_feat.empty:
            continue

        student_data = student_feat.iloc[0].to_dict()
        raw_student = students_df[students_df["student_id"] == sid].iloc[0].to_dict()
        student_data.update(raw_student)

        student_skills = student_data.get("skill_list", [])
        scorecard = check_criteria(student_data, company_data, student_skills)
        summary = scorecard.get("_summary", {})

        score = 0.0
        if MODEL_LOADED:
            try:
                result = run_inference(student_data, company_data, model, scaler, feature_cols)
                score = result["score"]
            except:
                pass

        results.append({
            "student_id": sid,
            "full_name": raw_student.get("full_name", ""),
            "department": raw_student.get("department", ""),
            "cgpa": raw_student.get("cgpa", 0),
            "eligible": summary.get("eligible", False),
            "score": round(score, 4),
            "hard_pass": summary.get("hard_pass", False),
            "hard_failures": summary.get("hard_failures", []),
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    eligible_count = sum(1 for r in results if r["eligible"])

    return {
        "company_id": request.company_id,
        "company_name": company_data.get("company_name", ""),
        "total_checked": len(results),
        "eligible_count": eligible_count,
        "ineligible_count": len(results) - eligible_count,
        "results": results,
    }


@app.get("/api/model/metrics")
async def get_model_metrics():
    """Get model training metrics."""
    metrics_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'metrics.json')
    if not os.path.exists(metrics_path):
        raise HTTPException(404, "Model metrics not found (model not trained yet)")

    with open(metrics_path) as f:
        metrics = json.load(f)

    fairness_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'fairness_report.json')
    fairness = None
    if os.path.exists(fairness_path):
        with open(fairness_path) as f:
            fairness = json.load(f)

    return {
        "model_loaded": MODEL_LOADED,
        "metrics": metrics,
        "fairness": fairness,
    }


@app.get("/api/stats")
async def get_stats():
    """Get system statistics."""
    if students_df is None:
        raise HTTPException(500, "Data not loaded")

    stats = {
        "total_students": len(students_df),
        "total_companies": len(companies_df) if companies_df is not None else 0,
        "departments": students_df["department"].value_counts().to_dict(),
        "avg_cgpa": round(float(students_df["cgpa"].mean()), 2),
        "cgpa_distribution": {
            "below_6": int((students_df["cgpa"] < 6).sum()),
            "6_to_7.5": int(((students_df["cgpa"] >= 6) & (students_df["cgpa"] < 7.5)).sum()),
            "7.5_to_8.5": int(((students_df["cgpa"] >= 7.5) & (students_df["cgpa"] < 8.5)).sum()),
            "8.5_to_9.5": int(((students_df["cgpa"] >= 8.5) & (students_df["cgpa"] < 9.5)).sum()),
            "above_9.5": int((students_df["cgpa"] >= 9.5).sum()),
        },
        "company_tiers": companies_df["tier"].value_counts().to_dict() if companies_df is not None else {},
        "model_loaded": MODEL_LOADED,
    }
    return stats


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
