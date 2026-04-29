def get_recommended_jobs(student: dict, all_jobs: list, eligible_job_ids: set) -> list:
    """
    Find cross-domain (non-eligible but skill-relevant) job recommendations.
    
    Strategy:
    1. Exclude jobs student is already eligible for
    2. Find jobs with skill overlap (if skills exist)
    3. Fallback: If no skills, show jobs from different branches (for diversity)
    4. Limit to top 10 by skill match score
    """
    recommendations = []
    student_skills = set(s.lower().strip() for s in (student.get("skills") or []) if s)
    student_branch = student.get("branch", "").lower()
    
    print(f"   Skill-based matching: {len(student_skills)} skills found")
    
    for job in all_jobs:
        # Skip already eligible jobs
        if job.get("id") in eligible_job_ids:
            continue
        
        job_id = job.get("id")
        job_role = job.get("role", "Unknown")
        job_company = job.get("company_name", "Unknown")
        job_branch = job.get("allowed_branches", [])
        
        # Try skill-based matching first
        if student_skills:
            required = set(s.lower().strip() for s in (job.get("required_skills") or []) if s)
            preferred = set(s.lower().strip() for s in (job.get("preferred_skills") or []) if s)
            all_job_skills = required | preferred
            
            if not all_job_skills:
                # Job has no skills listed, skip
                continue
            
            # Calculate overlap percentage (40% threshold instead of 50%)
            overlap = len(student_skills & all_job_skills) / len(all_job_skills) if all_job_skills else 0
            
            if overlap >= 0.4:
                recommendations.append({
                    **job,
                    "skill_match": round(overlap, 2),
                    "match_reason": f"{int(overlap*100)}% skill overlap"
                })
        
        # Fallback: If no student skills, show cross-branch opportunities
        elif job_branch and student_branch and student_branch not in [b.lower() for b in job_branch]:
            recommendations.append({
                **job,
                "skill_match": 0.5,
                "match_reason": "Cross-domain opportunity"
            })
    
    # Sort by skill match, limit to top 10
    recommendations = sorted(recommendations, key=lambda x: x["skill_match"], reverse=True)[:10]
    
    return recommendations
