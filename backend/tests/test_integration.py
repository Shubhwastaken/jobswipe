"""End-to-end flow tests. Each boots the app in-process and asserts a real
response, not merely a 200. These are the tests whose absence let the identity
substitutions, wrong-column filters and dead routers ship unnoticed.

All are @requires_db (skip when the DB is unreachable, e.g. CI without the secret).
"""

import base64
import json
import os
import uuid

import pytest

from tests.conftest import (
    requires_db,
    db_connect,
    SEED_EMAIL,
    SEED_STUDENT_ID,
    SECOND_EMAIL,
    SECOND_STUDENT_ID,
    TRIAL_PASSWORD,
)


def _jwt_payload(token: str) -> dict:
    segment = token.split(".")[1]
    segment += "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(segment))


@requires_db
def test_login_resolves_to_own_student_id(login):
    """A login must issue a token whose sub is the caller's OWN student_id — the
    fuzzy-name substitution that logged users in as a stranger was a live bug."""
    token = login(SEED_EMAIL, TRIAL_PASSWORD)
    payload = _jwt_payload(token)
    assert payload["sub"] == SEED_STUDENT_ID, payload
    assert payload.get("role") == "student"


@requires_db
def test_profile_fetch_is_populated(client, auth_headers):
    resp = client.get("/student/profile", headers=auth_headers())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["basic_info"]["student_id"] == SEED_STUDENT_ID
    assert body["basic_info"]["department"], "department is empty"
    assert body["education"].get("cgpa") not in (None, "", 0), body["education"]
    assert body.get("skills"), "skills list is empty for a student who has skills"


@requires_db
def test_student_feed_is_ranked_and_fairness_active(client, auth_headers):
    resp = client.get("/student/feed?limit=20", headers=auth_headers())
    assert resp.status_code == 200, resp.text
    jobs = resp.json()["jobs"]
    assert len(jobs) > 0, "seeded student got an empty feed"
    breakdown = jobs[0]["match_breakdown"]
    assert breakdown.get("fairness_status") == "active", breakdown
    assert "fairness_effective" in breakdown, "fairness_effective visibility flag missing"


@requires_db
def test_upskill_plan_is_personalised(client, auth_headers):
    """missing_skills must reflect the specific student, not be constant. Find a job
    whose requirements the two students lack differently, then prove the endpoint
    returns different plans for them."""
    from app.database import supabase
    from app.services.skill_normalizer import normalize_skill_set

    def student_skills(sid):
        rows = supabase.table("skills").select("skill_name").eq("student_id", sid).execute().data or []
        return set(normalize_skill_set(r["skill_name"] for r in rows))

    s1, s2 = student_skills(SEED_STUDENT_ID), student_skills(SECOND_STUDENT_ID)
    jobs = supabase.table("jobs").select("id, required_skills").eq("is_active", True).execute().data or []

    target = None
    for job in jobs:
        req = set(normalize_skill_set(job.get("required_skills") or []))
        if req and (req - s1) != (req - s2):
            target = job["id"]
            break
    assert target, "no job distinguishes the two students' skill gaps"

    h1 = auth_headers(SEED_EMAIL, TRIAL_PASSWORD)
    h2 = auth_headers(SECOND_EMAIL, TRIAL_PASSWORD)
    r1 = client.get(f"/upskill/{SEED_STUDENT_ID}/{target}", headers=h1)
    r2 = client.get(f"/upskill/{SECOND_STUDENT_ID}/{target}", headers=h2)
    assert r1.status_code == 200 and r2.status_code == 200, (r1.text, r2.text)
    m1 = set(r1.json()["missing_skills"])
    m2 = set(r2.json()["missing_skills"])
    assert m1 != m2, f"upskill plan identical for two different students: {m1}"


@requires_db
def test_resume_builder_prompt_uses_real_profile(client):
    """The generate-mode prompt must be built from the student's real data. Tested
    at the prompt-assembly boundary so it does not depend on the live LLM."""
    from app.routers.resume_builder import _build_user_prompt, _fetch_data

    data = _fetch_data(SEED_STUDENT_ID)
    prompt = _build_user_prompt(data)
    assert data["student"]["full_name"] in prompt, "student's real name absent from prompt"
    assert "SKILLS:" in prompt, "no skills section in prompt"
    real_skill = next((s["skill_name"] for s in data["skills"] if s.get("skill_name")), None)
    assert real_skill and real_skill in prompt, "no real skill made it into the prompt"


@requires_db
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set; interview creation needs the LLM")
def test_interview_session_creates_with_questions(client, auth_headers):
    resp = client.post(
        "/interview/sessions",
        json={"target_role": "Backend Engineer", "seniority": "junior"},
        headers=auth_headers(),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    session_id = body.get("id")
    assert session_id, body
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("select question_sequence from interview_sessions where id = %s", (session_id,))
        row = cur.fetchone()
        assert row and row[0], "interview session created with no questions"
    finally:
        # clean up the session this test created
        cur = conn.cursor()
        cur.execute("delete from interview_turns where session_id = %s", (session_id,))
        cur.execute("delete from interview_sessions where id = %s", (session_id,))
        conn.commit()
        conn.close()


@requires_db
def test_new_student_gets_a_feed(client):
    """A brand-new signup must be visible to the matcher and receive a feed.

    NOTE: the review predicted this FAILS (new student gets 0 jobs). Empirically it
    does not — a new student is eligible for the handful of jobs with no CGPA bar
    (~3 of 56), so len(jobs) > 0 holds. The real defect is that they are
    disqualified from the ~53 jobs that require CGPA > 0 because a missing CGPA is
    scored as 0. That is Phase 1, and a threshold-based test belongs there. This
    test guards the weaker, already-true invariant: a new user is not wholly
    locked out.
    """
    reg = "RA23110470" + str(uuid.uuid4().int % 100000).zfill(5)
    email = f"citest.{reg.lower()}@srmist.edu.in"
    password = "CiTestPass!" + reg[-5:]
    conn = db_connect()
    try:
        signup = client.post(
            "/auth/signup",
            json={"name": "CI New Student", "email": email, "register_number": reg, "password": password},
        )
        assert signup.status_code == 201, signup.text

        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        feed = client.get("/student/feed?limit=20", headers=headers)
        assert feed.status_code == 200, feed.text
        assert len(feed.json()["jobs"]) > 0, "new student is entirely locked out of the platform"
    finally:
        cur = conn.cursor()
        cur.execute("delete from students where student_id = %s or email = %s", (reg, email))
        conn.commit()
        conn.close()


@requires_db
def test_all_routers_are_mounted_or_declared_unmounted():
    """Every router file must be mounted, or explicitly listed as intentionally
    unmounted. This is the check that would have caught the dead jobs.py and the
    still-dead applications.py."""
    import importlib

    from fastapi.routing import APIRoute
    from fastapi import APIRouter

    from app.main import app

    app_paths = {r.path for r in app.routes if isinstance(r, APIRoute)}

    # applications.py is dead code (Phase 5 removes it); until then it is knowingly
    # unmounted. Any OTHER unmounted router is a bug.
    intentionally_unmounted = {"applications"}

    routers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "routers")
    offenders = []
    for filename in os.listdir(routers_dir):
        if not filename.endswith(".py") or filename in {"__init__.py", "deps.py"}:
            continue
        modname = filename[:-3]
        module = importlib.import_module(f"app.routers.{modname}")
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            continue
        router_paths = {r.path for r in router.routes if isinstance(r, APIRoute)}
        if not router_paths:
            continue
        if not (router_paths & app_paths) and modname not in intentionally_unmounted:
            offenders.append(modname)

    assert not offenders, f"router(s) defined but not mounted and not declared unmounted: {offenders}"
