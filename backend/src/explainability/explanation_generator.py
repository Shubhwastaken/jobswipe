"""
Explanation Generator: Produces human-readable explanations for eligibility decisions.
Every decision must have a clear, criteria-tied reason — no black-box outputs.
"""


def generate_explanation(scorecard, company_name="the company"):
    """
    Generate a human-readable explanation for an eligibility decision.
    Returns a structured explanation with emoji status indicators.
    """
    summary = scorecard.get("_summary", {})
    eligible = summary.get("eligible", False)

    lines = []
    lines.append(f"{'✅ ELIGIBLE' if eligible else '❌ INELIGIBLE'} for {company_name}")
    lines.append("=" * 50)

    # Hard criteria
    lines.append("\n📋 Hard Criteria (must all pass):")
    hard_keys = ["cgpa_check", "10th_check", "12th_check", "backlog_check", "department_check"]
    for key in hard_keys:
        if key in scorecard:
            item = scorecard[key]
            status = "✅" if item["passed"] else "❌"
            lines.append(f"  {status} {item['message']}")

    # Soft criteria
    lines.append("\n📊 Soft Criteria (scored):")
    soft_keys = ["required_skills_score", "preferred_skills_score",
                 "internship_score", "project_score",
                 "research_score", "cert_score"]
    for key in soft_keys:
        if key in scorecard:
            item = scorecard[key]
            status = "✅" if item.get("passed", True) else "⚠️"
            lines.append(f"  {status} {item['message']}")

    return "\n".join(lines)


def generate_detailed_report(result, company_name="the company"):
    """
    Generate a detailed report from an inference result.
    """
    lines = []

    # Header
    if result["eligible"]:
        lines.append(f"## ✅ ELIGIBLE for {company_name}")
    else:
        lines.append(f"## ❌ INELIGIBLE for {company_name}")

    lines.append(f"**Score:** {result['score']:.2f} / 1.00")
    lines.append(f"**Reason:** {result['message']}")

    # Hard failures
    if result.get("hard_failures"):
        lines.append("\n### 🚫 Disqualifying Factors:")
        for failure in result["hard_failures"]:
            item = result["scorecard"].get(failure, {})
            lines.append(f"- **{failure}**: {item.get('message', 'Failed')}")

    # Detailed scorecard
    if result.get("scorecard"):
        lines.append("\n### 📋 Full Criteria Breakdown:")
        explanation = generate_explanation(result["scorecard"], company_name)
        lines.append(explanation)

    return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    from src.explainability.criteria_checker import check_criteria

    student = {
        "cgpa": 6.2, "10th_marks": 72, "12th_marks": 68,
        "active_backlogs": 1, "department": "ECE",
        "total_internship_months": 0, "num_projects": 1,
        "max_project_complexity": 1, "num_papers": 0,
        "max_cert_tier": 1,
    }
    company = {
        "min_cgpa": 7.0, "min_10th": 60, "min_12th": 60,
        "max_active_backlogs": 0,
        "allowed_departments": "CSE,IT,AIML",
        "required_skills": "Python,Java,SQL",
        "preferred_skills": "React,AWS",
        "min_internship_months": 2, "min_projects": 2,
        "project_complexity_min": "Intermediate",
        "requires_research_paper": False,
        "cert_tier_required": "National",
    }
    skills = ["Python", "C"]

    scorecard = check_criteria(student, company, skills)
    print(generate_explanation(scorecard, "Google India"))
