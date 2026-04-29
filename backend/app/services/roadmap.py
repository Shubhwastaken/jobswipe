def generate_roadmap(student: dict, target_job: dict, supabase) -> dict:
    student_skills = set(s.lower().strip() for s in (student.get("skills") or []))
    job_skills = set(s.lower().strip() for s in (target_job.get("required_skills") or []))
    missing = job_skills - student_skills

    roadmap = []
    total_weeks = 0
    for skill in sorted(missing):
        skill_result = supabase.table("skills_graph").select("*").eq("skill_name", skill).maybe_single().execute()
        skill_data = skill_result.data if skill_result else None
        
        resources_result = supabase.table("learning_resources").select("*").eq("skill_name", skill).limit(3).execute()
        resources = resources_result.data if resources_result else []

        weeks = skill_data.get("avg_learning_weeks", 3) if skill_data else 3
        total_weeks += weeks
        roadmap.append({
            "skill": skill,
            "weeks": weeks,
            "difficulty": skill_data.get("difficulty_level", "Intermediate") if skill_data else "Intermediate",
            "resources": resources or [],
        })

    order = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    roadmap.sort(key=lambda x: order.get(x.get("difficulty"), 1))

    return {
        "missing_skills": list(missing),
        "roadmap": roadmap,
        "estimated_weeks": total_weeks,
    }
