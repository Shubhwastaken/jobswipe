def get_eligible_jobs(student: dict, all_jobs: list) -> list:
    """Filter jobs based on student eligibility with dynamic batch year logic and skill/experience checks.
    
    Eligibility criteria (all must pass):
    - CGPA: student.cgpa >= job.min_cgpa (range-based)
    - Backlogs: student.active_backlogs <= job.max_backlogs (range-based)
    - Branch: student.branch in job.allowed_branches (exact match) OR allowed_branches is empty/None
    - Batch Year: Dynamic logic based on graduation timing:
      * A student with batch_year B will graduate in year B (or B+3/4 for 4-year courses)
      * A job for batch_year J is hiring from students graduating in year J
      * Student is eligible if: student_batch_year <= job_batch_year + 1
        (can sit for same year or up to 1 year later placements)
      * This allows final year students to sit while preventing future batches from applying
    - Skills: At least 30% overlap with required skills OR 50% with preferred skills
    - Experience: At least 1 project mentioned if job requires experience
    """
    eligible = []
    failed_cgpa = 0
    failed_backlogs = 0
    failed_branch = 0
    failed_batch = 0
    failed_skills = 0
    failed_experience = 0
    
    student_skills = set(s.lower().strip() for s in (student.get("skills") or []))
    student_projects = student.get("projects") or []
    has_experience = len(student_projects) > 0
    
    for job in all_jobs:
        job_id = job.get("id", "unknown")
        role = job.get("role", "Unknown")
        company = job.get("company_name", "Unknown")
        
        reasons = []  # Collect eligibility reasons
        
        # CGPA check: student must meet or exceed minimum CGPA
        if (student.get("cgpa") is not None and job.get("min_cgpa") is not None):
            if student["cgpa"] < job["min_cgpa"]:
                failed_cgpa += 1
                continue
            else:
                reasons.append(f"CGPA {student['cgpa']} meets minimum {job['min_cgpa']}")
        
        # Backlogs check: student must have fewer or equal backlogs than max allowed
        if (student.get("active_backlogs") is not None and job.get("max_backlogs") is not None):
            if student["active_backlogs"] > job["max_backlogs"]:
                failed_backlogs += 1
                continue
            else:
                reasons.append(f"Backlogs {student['active_backlogs']} within limit {job['max_backlogs']}")
        
        # Branch check: student's branch must be in allowed branches (or no restriction)
        if student.get("branch") and job.get("allowed_branches") and len(job.get("allowed_branches", [])) > 0:
            if student["branch"] not in job["allowed_branches"]:
                failed_branch += 1
                continue
            else:
                reasons.append(f"Branch {student['branch']} matches allowed branches")
        
        # Batch year check: Dynamic logic for placement eligibility
        # A student graduating in year B can sit for placements from year B or year B-1
        # (allowing some flexibility for rollover placements)
        if student.get("batch_year") is not None and job.get("batch_year") is not None:
            # Student can apply if: student_batch_year <= job_batch_year + 1
            # This allows: same year (2025 student for 2025 job), or late placements (2025 student for 2026 job)
            # But prevents: 2027 student from applying to 2025 job (already graduated)
            if student["batch_year"] > job["batch_year"] + 1:
                failed_batch += 1
                continue
            else:
                reasons.append(f"Batch year {student['batch_year']} eligible for {job['batch_year']} placements")
        
        # Skills check: At least 30% required skills match OR 50% preferred skills match
        required_skills = set(s.lower().strip() for s in job.get("required_skills") or [])
        preferred_skills = set(s.lower().strip() for s in (job.get("preferred_skills") or []))
        
        req_overlap = len(required_skills & student_skills) / len(required_skills) if required_skills else 1.0
        pref_overlap = len(preferred_skills & student_skills) / len(preferred_skills) if preferred_skills else 1.0
        
        if req_overlap < 0.3 and pref_overlap < 0.5:
            failed_skills += 1
            continue
        else:
            if req_overlap >= 0.3:
                reasons.append(f"Required skills match: {req_overlap:.1%}")
            if pref_overlap >= 0.5:
                reasons.append(f"Preferred skills match: {pref_overlap:.1%}")
        
        # Experience check: If job requires experience (has required_skills), student should have projects
        if required_skills and not has_experience:
            failed_experience += 1
            continue
        elif has_experience:
            reasons.append(f"Has {len(student_projects)} relevant projects")
        
        # If all checks pass, add to eligible with reasons
        job_with_reasons = job.copy()
        job_with_reasons["eligibility_reasons"] = reasons
        eligible.append(job_with_reasons)
    
    # DEBUG: Log summary
    total = len(all_jobs)
    print(f"   Eligibility filtering results:")
    print(f"   - CGPA mismatch: {failed_cgpa}")
    print(f"   - Backlogs mismatch: {failed_backlogs}")
    print(f"   - Branch mismatch: {failed_branch}")
    print(f"   - Batch year mismatch: {failed_batch}")
    print(f"   - Skills mismatch: {failed_skills}")
    print(f"   - Experience mismatch: {failed_experience}")
    print(f"   - Eligible: {len(eligible)}/{total}")
    
    return eligible
