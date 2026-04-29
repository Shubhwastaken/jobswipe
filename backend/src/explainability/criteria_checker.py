"""
Layer 1: Criteria Matching Engine (Rule-Based, Transparent)
For each company–student pair, computes a detailed criteria scorecard.
Every decision is explainable — no black box here.
"""

import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

CERT_TIER_ORDER = ["None", "Local", "National", "Global_Standard", "Global_Premium"]
COMPLEXITY_ORDER = ["None", "Basic", "Intermediate", "Advanced"]
INTERN_TIER_ORDER = ["Any", "Tier3", "Tier2", "Tier1", "Tier1_or_Tier2"]


def tier_meets_requirement(student_tier_value, required_tier_str, tier_order):
    """Check if student's tier level meets or exceeds the requirement."""
    if required_tier_str in ("None", "Any", "", None):
        return True
    if required_tier_str not in tier_order:
        return True
    req_idx = tier_order.index(required_tier_str)
    return student_tier_value >= req_idx


def check_criteria(student_data, company_data, student_skills=None):
    """
    Run all criteria checks for one student–company pair.
    Returns a detailed scorecard dict with pass/fail for each criterion.
    """
    scorecard = {}

    # --- HARD CHECKS (any failure = immediate disqualification) ---

    # CGPA
    cgpa = float(student_data.get("cgpa", 0))
    min_cgpa = float(company_data.get("min_cgpa", 0))
    scorecard["cgpa_check"] = {
        "passed": cgpa >= min_cgpa,
        "student_value": cgpa,
        "required_value": min_cgpa,
        "is_hard": True,
        "message": f"CGPA {cgpa} {'meets' if cgpa >= min_cgpa else 'does not meet'} minimum {min_cgpa}"
    }

    # 10th marks
    marks_10 = float(student_data.get("10th_marks", 0))
    min_10 = float(company_data.get("min_10th", 0))
    scorecard["10th_check"] = {
        "passed": marks_10 >= min_10,
        "student_value": marks_10,
        "required_value": min_10,
        "is_hard": True,
        "message": f"10th marks {marks_10} {'meets' if marks_10 >= min_10 else 'does not meet'} minimum {min_10}"
    }

    # 12th marks
    marks_12 = float(student_data.get("12th_marks", 0))
    min_12 = float(company_data.get("min_12th", 0))
    scorecard["12th_check"] = {
        "passed": marks_12 >= min_12,
        "student_value": marks_12,
        "required_value": min_12,
        "is_hard": True,
        "message": f"12th marks {marks_12} {'meets' if marks_12 >= min_12 else 'does not meet'} minimum {min_12}"
    }

    # Active backlogs
    active = int(student_data.get("active_backlogs", 0))
    max_backlogs = int(company_data.get("max_active_backlogs", 0))
    scorecard["backlog_check"] = {
        "passed": active <= max_backlogs,
        "student_value": active,
        "required_value": max_backlogs,
        "is_hard": True,
        "message": f"Active backlogs {active} {'within' if active <= max_backlogs else 'exceeds'} limit of {max_backlogs}"
    }

    # Department
    dept = student_data.get("department", "")
    allowed = [d.strip() for d in str(company_data.get("allowed_departments", "")).split(",")]
    dept_pass = dept in allowed
    scorecard["department_check"] = {
        "passed": dept_pass,
        "student_value": dept,
        "required_value": ", ".join(allowed),
        "is_hard": True,
        "message": f"Department {dept} {'is in' if dept_pass else 'is not in'} allowed list: {', '.join(allowed)}"
    }

    # --- SOFT CHECKS (scored, not pass/fail) ---

    # Required skills
    if student_skills is None:
        student_skills = []
    student_skills_lower = [s.lower().strip() for s in student_skills]

    req_skills_str = str(company_data.get("required_skills", ""))
    if req_skills_str and req_skills_str != "nan":
        req_skills = [s.strip() for s in req_skills_str.split(",")]
        matched = [s for s in req_skills if s.lower() in student_skills_lower]
        missing = [s for s in req_skills if s.lower() not in student_skills_lower]
        req_ratio = len(matched) / len(req_skills) if req_skills else 1.0
    else:
        req_skills = []
        matched = []
        missing = []
        req_ratio = 1.0

    scorecard["required_skills_score"] = {
        "passed": req_ratio >= 0.5,
        "score": round(req_ratio, 3),
        "matched": matched,
        "missing": missing,
        "is_hard": False,
        "message": f"Required skills: {len(matched)}/{len(req_skills)} matched" +
                   (f" (missing: {', '.join(missing)})" if missing else "")
    }

    # Preferred skills
    pref_skills_str = str(company_data.get("preferred_skills", ""))
    if pref_skills_str and pref_skills_str != "nan":
        pref_skills = [s.strip() for s in pref_skills_str.split(",")]
        pref_matched = [s for s in pref_skills if s.lower() in student_skills_lower]
        pref_ratio = len(pref_matched) / len(pref_skills) if pref_skills else 1.0
    else:
        pref_skills = []
        pref_matched = []
        pref_ratio = 1.0

    scorecard["preferred_skills_score"] = {
        "passed": True,  # Preferred skills don't cause failure
        "score": round(pref_ratio, 3),
        "matched": pref_matched,
        "is_hard": False,
        "message": f"Preferred skills: {len(pref_matched)}/{len(pref_skills)} matched"
    }

    # Internship check
    intern_months = float(student_data.get("total_internship_months", 0))
    min_intern = float(company_data.get("min_internship_months", 0))
    scorecard["internship_score"] = {
        "passed": intern_months >= min_intern,
        "student_value": intern_months,
        "required_value": min_intern,
        "is_hard": False,
        "message": f"Internship: {intern_months} months {'meets' if intern_months >= min_intern else 'does not meet'} minimum {min_intern} months"
    }

    # Project check
    num_projects = int(student_data.get("num_projects", 0))
    min_projects = int(company_data.get("min_projects", 0))
    scorecard["project_score"] = {
        "passed": num_projects >= min_projects,
        "student_value": num_projects,
        "required_value": min_projects,
        "is_hard": False,
        "message": f"Projects: {num_projects} {'meets' if num_projects >= min_projects else 'does not meet'} minimum {min_projects}"
    }

    # Research paper check
    num_papers = int(student_data.get("num_papers", 0))
    requires_paper = company_data.get("requires_research_paper", False)
    if isinstance(requires_paper, str):
        requires_paper = requires_paper.lower() == "true"
    scorecard["research_score"] = {
        "passed": not requires_paper or num_papers > 0,
        "student_value": num_papers,
        "required_value": 1 if requires_paper else 0,
        "is_hard": False,
        "message": f"Research papers: {num_papers}" +
                   (" (required)" if requires_paper else " (not required)")
    }

    # Certification check
    max_cert_tier = int(student_data.get("max_cert_tier", 0))
    cert_required = str(company_data.get("cert_tier_required", "None"))
    cert_req_level = CERT_TIER_ORDER.index(cert_required) if cert_required in CERT_TIER_ORDER else 0
    scorecard["cert_score"] = {
        "passed": max_cert_tier >= cert_req_level,
        "student_value": max_cert_tier,
        "required_value": cert_req_level,
        "is_hard": False,
        "message": f"Certification tier: student has tier {max_cert_tier}, requires tier {cert_req_level} ({cert_required})"
    }

    # --- OVERALL VERDICT ---
    hard_checks = [v for v in scorecard.values() if v.get("is_hard")]
    hard_pass = all(c["passed"] for c in hard_checks)

    soft_checks = [v for v in scorecard.values() if not v.get("is_hard")]
    soft_passed = sum(1 for c in soft_checks if c.get("passed", True))
    soft_total = len(soft_checks)

    scorecard["_summary"] = {
        "hard_pass": hard_pass,
        "soft_score": soft_passed / soft_total if soft_total > 0 else 1.0,
        "eligible": hard_pass and (soft_passed / soft_total >= 0.4 if soft_total > 0 else True),
        "hard_failures": [k for k, v in scorecard.items()
                          if v.get("is_hard") and not v.get("passed") and k != "_summary"],
        "soft_weaknesses": [k for k, v in scorecard.items()
                            if not v.get("is_hard") and not v.get("passed", True) and k != "_summary"],
    }

    return scorecard


if __name__ == "__main__":
    # Quick demo
    student = {
        "cgpa": 8.1, "10th_marks": 85, "12th_marks": 82,
        "active_backlogs": 0, "department": "CSE",
        "total_internship_months": 3, "num_projects": 3,
        "max_project_complexity": 2, "num_papers": 0,
        "max_cert_tier": 3,
    }
    company = {
        "min_cgpa": 7.5, "min_10th": 60, "min_12th": 60,
        "max_active_backlogs": 0, "allowed_departments": "CSE,IT,AIML",
        "required_skills": "Python,SQL,React",
        "preferred_skills": "TensorFlow,AWS",
        "min_internship_months": 2, "min_projects": 2,
        "project_complexity_min": "Intermediate",
        "requires_research_paper": False, "cert_tier_required": "National",
    }
    skills = ["Python", "SQL", "Java", "TensorFlow"]

    result = check_criteria(student, company, skills)
    for key, val in result.items():
        if key == "_summary":
            print(f"\n{'='*50}")
            print(f"ELIGIBLE: {'✅ YES' if val['eligible'] else '❌ NO'}")
            if val["hard_failures"]:
                print(f"Hard failures: {val['hard_failures']}")
            if val["soft_weaknesses"]:
                print(f"Soft weaknesses: {val['soft_weaknesses']}")
        else:
            status = "✅" if val.get("passed") else "❌"
            print(f"{status} {key}: {val['message']}")
