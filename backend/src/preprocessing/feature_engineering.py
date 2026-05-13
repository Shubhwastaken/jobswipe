"""
Feature Engineering: Aggregate all sub-tables into a single feature vector per student.
This is the data preparation layer that feeds into the ML model.

ANTI-BIAS: name, gender, board_type are EXCLUDED from features.
"""

import pandas as pd
import numpy as np
import os

try:
    from app.services.data_paths import data_dir
    DATA_DIR = str(data_dir())
except Exception:
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# Tier encoding maps (ordinal, higher = better)
CERT_TIER_MAP = {
    "Local": 1,
    "National": 2,
    "Global_Standard": 3,
    "Global_Premium": 4,
}

PROJECT_COMPLEXITY_MAP = {
    "Basic": 1,
    "Intermediate": 2,
    "Advanced": 3,
}

INTERNSHIP_TIER_MAP = {
    "NGO": 1,
    "Startup": 2,
    "Tier3": 3,
    "Tier2": 4,
    "Tier1": 5,
}

PAPER_TIER_MAP = {
    "Non-indexed": 1,
    "Conference": 2,
    "Q3": 3,
    "Q2": 4,
    "Q1": 5,
}

COMPANY_COMPLEXITY_MAP = {
    "None": 0,
    "Basic": 1,
    "Intermediate": 2,
    "Advanced": 3,
}

COMPANY_CERT_TIER_MAP = {
    "None": 0,
    "Local": 1,
    "National": 2,
    "Global_Standard": 3,
    "Global_Premium": 4,
}


def load_all_data():
    """Load all CSV files into DataFrames."""
    students = pd.read_csv(os.path.join(DATA_DIR, "students.csv"))
    certs = pd.read_csv(os.path.join(DATA_DIR, "certifications.csv"))
    projects = pd.read_csv(os.path.join(DATA_DIR, "projects.csv"))
    internships = pd.read_csv(os.path.join(DATA_DIR, "internships.csv"))
    papers = pd.read_csv(os.path.join(DATA_DIR, "research_papers.csv"))
    skills = pd.read_csv(os.path.join(DATA_DIR, "skills.csv"))
    companies = pd.read_csv(os.path.join(DATA_DIR, "companies.csv"))
    return students, certs, projects, internships, papers, skills, companies


def build_student_features(students, certs, projects, internships, papers, skills):
    """
    Build a feature DataFrame for each student.
    Returns a DataFrame indexed by student_id with all engineered features.

    ANTI-BIAS: Excludes full_name, gender, 10th_board, 12th_board from features.
    These are kept in the students table for audit only.
    """
    features = pd.DataFrame()
    features["student_id"] = students["student_id"]

    # --- Academic features (normalized, board-agnostic) ---
    features["cgpa"] = students["cgpa"]
    features["cgpa_normalized"] = students["cgpa"] / 10.0
    features["10th_normalized"] = students["10th_marks"] / 100.0
    features["12th_normalized"] = students["12th_marks"] / 100.0
    features["backlogs_history"] = students["backlogs_history"]
    features["active_backlogs"] = students["active_backlogs"]

    # --- Department (kept as string for matching, encoded later) ---
    features["department"] = students["department"]

    # --- Certification aggregates ---
    cert_agg = certs.copy()
    cert_agg["tier_encoded"] = cert_agg["tier"].map(CERT_TIER_MAP).fillna(0)

    cert_features = cert_agg.groupby("student_id").agg(
        num_certs=("cert_id", "count"),
        num_global_premium=("tier_encoded", lambda x: (x == 4).sum()),
        num_global_standard=("tier_encoded", lambda x: (x == 3).sum()),
        num_national=("tier_encoded", lambda x: (x == 2).sum()),
        num_local=("tier_encoded", lambda x: (x == 1).sum()),
        max_cert_tier=("tier_encoded", "max"),
    ).reset_index()

    features = features.merge(cert_features, on="student_id", how="left")
    cert_cols = ["num_certs", "num_global_premium", "num_global_standard",
                 "num_national", "num_local", "max_cert_tier"]
    features[cert_cols] = features[cert_cols].fillna(0).astype(int)

    # --- Project aggregates ---
    proj_agg = projects.copy()
    proj_agg["complexity_encoded"] = proj_agg["complexity"].map(PROJECT_COMPLEXITY_MAP).fillna(0)

    proj_features = proj_agg.groupby("student_id").agg(
        num_projects=("project_id", "count"),
        max_project_complexity=("complexity_encoded", "max"),
        num_advanced_projects=("complexity_encoded", lambda x: (x == 3).sum()),
        num_deployed=("has_deployment", "sum"),
        num_with_github=("has_github", "sum"),
        total_project_weeks=("duration_weeks", "sum"),
    ).reset_index()

    features = features.merge(proj_features, on="student_id", how="left")
    proj_cols = ["num_projects", "max_project_complexity", "num_advanced_projects",
                 "num_deployed", "num_with_github", "total_project_weeks"]
    features[proj_cols] = features[proj_cols].fillna(0).astype(int)

    # --- Internship aggregates ---
    intern_agg = internships.copy()
    intern_agg["tier_encoded"] = intern_agg["company_tier"].map(INTERNSHIP_TIER_MAP).fillna(0)

    intern_features = intern_agg.groupby("student_id").agg(
        num_internships=("internship_id", "count"),
        total_internship_months=("duration_months", "sum"),
        max_internship_tier=("tier_encoded", "max"),
    ).reset_index()

    features = features.merge(intern_features, on="student_id", how="left")
    features["num_internships"] = features["num_internships"].fillna(0).astype(int)
    features["total_internship_months"] = features["total_internship_months"].fillna(0.0)
    features["max_internship_tier"] = features["max_internship_tier"].fillna(0).astype(int)

    # --- Research paper aggregates ---
    paper_agg = papers.copy()
    paper_agg["tier_encoded"] = paper_agg["tier"].map(PAPER_TIER_MAP).fillna(0)

    paper_features = paper_agg.groupby("student_id").agg(
        num_papers=("paper_id", "count"),
        max_paper_tier=("tier_encoded", "max"),
        num_first_author=("is_first_author", "sum"),
    ).reset_index()

    features = features.merge(paper_features, on="student_id", how="left")
    paper_cols = ["num_papers", "max_paper_tier", "num_first_author"]
    features[paper_cols] = features[paper_cols].fillna(0).astype(int)

    # --- Skills aggregates ---
    skill_features = skills.groupby("student_id").agg(
        num_skills=("skill_name", "count"),
        num_advanced_skills=("proficiency", lambda x: (x == "Advanced").sum()),
        num_verified_skills=("verified", "sum"),
    ).reset_index()

    features = features.merge(skill_features, on="student_id", how="left")
    skill_cols = ["num_skills", "num_advanced_skills", "num_verified_skills"]
    features[skill_cols] = features[skill_cols].fillna(0).astype(int)

    # Store skill names per student for matching later
    skill_lists = skills.groupby("student_id")["skill_name"].apply(list).reset_index()
    skill_lists.columns = ["student_id", "skill_list"]
    features = features.merge(skill_lists, on="student_id", how="left")
    features["skill_list"] = features["skill_list"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    return features


def compute_skill_match(student_skills, required_skills_str, preferred_skills_str):
    """
    Compute skill match ratios for a student against company requirements.
    Returns (required_match_ratio, preferred_match_ratio).
    """
    if not student_skills:
        student_skills = []

    student_skills_lower = [s.lower().strip() for s in student_skills]

    # Required skills
    if pd.isna(required_skills_str) or required_skills_str == "":
        req_ratio = 1.0
    else:
        req_skills = [s.lower().strip() for s in str(required_skills_str).split(",")]
        if len(req_skills) == 0:
            req_ratio = 1.0
        else:
            matched = sum(1 for s in req_skills if s in student_skills_lower)
            req_ratio = matched / len(req_skills)

    # Preferred skills
    if pd.isna(preferred_skills_str) or preferred_skills_str == "":
        pref_ratio = 1.0
    else:
        pref_skills = [s.lower().strip() for s in str(preferred_skills_str).split(",")]
        if len(pref_skills) == 0:
            pref_ratio = 1.0
        else:
            matched = sum(1 for s in pref_skills if s in student_skills_lower)
            pref_ratio = matched / len(pref_skills)

    return req_ratio, pref_ratio


def build_pair_features(student_features, companies):
    """
    Build (student × company) pair feature vectors for model training.
    Each row = one student–company eligibility assessment.
    """
    pairs = []

    for _, company in companies.iterrows():
        company_id = company["company_id"]
        allowed_depts = [d.strip() for d in str(company["allowed_departments"]).split(",")]

        for _, student in student_features.iterrows():
            # Department match
            dept_match = 1 if student["department"] in allowed_depts else 0

            # Skill matching
            req_ratio, pref_ratio = compute_skill_match(
                student["skill_list"],
                company["required_skills"],
                company["preferred_skills"]
            )

            # Project complexity comparison
            company_min_complexity = COMPANY_COMPLEXITY_MAP.get(
                company["project_complexity_min"], 0
            )
            meets_project_complexity = 1 if student["max_project_complexity"] >= company_min_complexity else 0

            # Cert tier comparison
            company_cert_req = COMPANY_CERT_TIER_MAP.get(
                str(company["cert_tier_required"]), 0
            )
            meets_cert_tier = 1 if student["max_cert_tier"] >= company_cert_req else 0

            pair = {
                "student_id": student["student_id"],
                "company_id": company_id,
                # Student features (bias-free)
                "cgpa_normalized": student["cgpa_normalized"],
                "10th_normalized": student["10th_normalized"],
                "12th_normalized": student["12th_normalized"],
                "active_backlogs": student["active_backlogs"],
                # Matching features
                "dept_match": dept_match,
                "required_skills_match_ratio": round(req_ratio, 3),
                "preferred_skills_match_ratio": round(pref_ratio, 3),
                # Aggregated student features
                "total_internship_months": student["total_internship_months"],
                "max_internship_tier": student["max_internship_tier"],
                "num_projects": student["num_projects"],
                "max_project_complexity": student["max_project_complexity"],
                "meets_project_complexity": meets_project_complexity,
                "num_global_premium_certs": student["num_global_premium"],
                "num_global_standard_certs": student["num_global_standard"],
                "num_national_certs": student["num_national"],
                "meets_cert_tier": meets_cert_tier,
                "num_papers": student["num_papers"],
                "max_paper_tier": student["max_paper_tier"],
                "num_advanced_skills": student["num_advanced_skills"],
                "num_verified_skills": student["num_verified_skills"],
            }
            pairs.append(pair)

    return pd.DataFrame(pairs)


if __name__ == "__main__":
    print("Loading data...")
    students, certs, projects, internships, papers, skills, companies = load_all_data()

    print("Building student feature vectors...")
    student_features = build_student_features(
        students, certs, projects, internships, papers, skills
    )
    print(f"  → {len(student_features)} students with {len(student_features.columns)} features")

    # Save intermediate features
    out_path = os.path.join(DATA_DIR, "student_features.csv")
    export = student_features.drop(columns=["skill_list"])
    export.to_csv(out_path, index=False)
    print(f"  → Saved to {out_path}")

    print("\nBuilding pair features (student × company)...")
    print("  (This may take a moment for 800 students × 50 companies = 40,000 pairs...)")
    pair_features = build_pair_features(student_features, companies)
    print(f"  → {len(pair_features)} pairs with {len(pair_features.columns)} features")

    pair_path = os.path.join(DATA_DIR, "pair_features.csv")
    pair_features.to_csv(pair_path, index=False)
    print(f"  → Saved to {pair_path}")
