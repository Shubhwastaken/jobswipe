def compute_bias_adjusted_score(student: dict, job: dict) -> float:
    """Bias reduction built in:\n    - CGPA scale reduced to 30%\n    - Skills are 50% (required + preferred)\n    - Project / JD textual overlap 20%\n    """

    # 1. CGPA score normalized
    student_cgpa = student.get("cgpa", 0.0) or 0.0
    min_cgpa = job.get("min_cgpa", 0.0) or 0.0
    cgpa_range = 10.0 - min_cgpa
    if cgpa_range <= 0:
        cgpa_score = 1.0
    else:
        cgpa_score = max(0.0, min(1.0, (student_cgpa - min_cgpa) / cgpa_range))

    # 2. Required skill overlap
    required = set(s.lower().strip() for s in job.get("required_skills") or [])
    student_skills = set(s.lower().strip() for s in (student.get("skills") or []))
    req_match = len(required & student_skills) / len(required) if required else 0.0

    # 3. Preferred skill overlap
    preferred = set(s.lower().strip() for s in (job.get("preferred_skills") or []))
    pref_match = len(preferred & student_skills) / len(preferred) if preferred else 0.0
    skill_score = 0.7 * req_match + 0.3 * pref_match

    # 4. Project relevance via JD similarity
    jd_lower = (job.get("job_description") or "").lower()
    projects_text = " ".join(student.get("projects") or []).lower()
    common_words = set(projects_text.split()) & set(jd_lower.split())
    stop_words = {"the", "a", "and", "in", "of", "to", "for", "with", "on", "is"}
    meaningful = common_words - stop_words
    project_score = min(len(meaningful) / 10.0, 1.0)

    final = (0.30 * cgpa_score) + (0.50 * skill_score) + (0.20 * project_score)
    return round(final, 4)
