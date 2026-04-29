"""
Store model results (eligibility + improvement plans) to Supabase.
"""

import json
import os
from datetime import datetime
from src.database.supabase_client import get_client


def store_eligibility_result(student_id, company_id, eligible, score,
                              criteria_breakdown, client=None):
    """Store a single eligibility result."""
    if client is None:
        client = get_client(use_service_key=True)

    # Serialize scorecard (remove non-serializable items)
    breakdown = {}
    for key, val in criteria_breakdown.items():
        if key == "_summary":
            breakdown[key] = {
                "hard_pass": val.get("hard_pass"),
                "soft_score": val.get("soft_score"),
                "eligible": val.get("eligible"),
                "hard_failures": val.get("hard_failures", []),
                "soft_weaknesses": val.get("soft_weaknesses", []),
            }
        else:
            breakdown[key] = {
                "passed": val.get("passed"),
                "message": val.get("message", ""),
            }

    record = {
        "student_id": student_id,
        "company_id": company_id,
        "eligible": eligible,
        "score": float(score),
        "criteria_breakdown": json.dumps(breakdown),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        client.table("eligibility_results").upsert(record).execute()
        return True
    except Exception as e:
        print(f"❌ Error storing result: {e}")
        return False


def store_improvement_plan(student_id, company_id, suggestions, client=None):
    """Store improvement plan for a student-company pair."""
    if client is None:
        client = get_client(use_service_key=True)

    record = {
        "student_id": student_id,
        "company_id": company_id,
        "suggestions": json.dumps(suggestions),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        client.table("improvement_plans").upsert(record).execute()
        return True
    except Exception as e:
        print(f"❌ Error storing plan: {e}")
        return False


def store_batch_results(results, client=None):
    """Store multiple eligibility results at once."""
    if client is None:
        client = get_client(use_service_key=True)

    success = 0
    for result in results:
        ok = store_eligibility_result(
            result["student_id"],
            result.get("company_id", ""),
            result["eligible"],
            result["score"],
            result.get("scorecard", {}),
            client=client
        )
        if ok:
            success += 1

    print(f"✅ Stored {success}/{len(results)} results")
    return success
