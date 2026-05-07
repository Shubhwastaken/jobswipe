"""
Skill Gap Simulator — Option 2: Skill Gap Prediction

For every student, simulates the counterfactual question:
  "If this student learned skill X, how much would their eligibility
   probability increase across the 50-company pool?"

Algorithm
─────────
For each student:
  1. Get their current eligibility probability across all companies (baseline)
  2. For each skill NOT already in their profile:
       a. Temporarily add the skill to their feature vector
       b. Re-compute eligibility probability for all 50 companies
       c. Δgain = mean(new_probs) - mean(baseline_probs)
  3. Rank skills by Δgain → top-K recommendations

This produces the labelled dataset:
    (student_id, skill_name, current_skills, avg_gain, max_gain, eligible_company_gain)

That dataset trains the surrogate recommender in skill_recommender.py.

Output: data/skill_gap_labels.csv
"""

import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
from tqdm import tqdm

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(__file__)
DATA_DIR  = os.path.join(_HERE, "..", "..", "data")
MODEL_DIR = os.path.join(_HERE, "..", "..", "models")

# All skills in the company pool (from generate_companies.py)
ALL_SKILLS = [
    "Python", "Java", "C", "C++", "JavaScript", "TypeScript", "SQL",
    "React", "Angular", "Node.js", "Django", "Flask", "Spring Boot",
    "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git",
    "MongoDB", "PostgreSQL", "MySQL", "Redis",
    "HTML/CSS", "REST APIs", "Linux", "Tableau", "Power BI",
    "Excel", "Communication", "Leadership",
]

FEATURE_COLS = [
    "cgpa_normalized", "10th_normalized", "12th_normalized",
    "active_backlogs", "dept_match",
    "required_skills_match_ratio", "preferred_skills_match_ratio",
    "total_internship_months", "max_internship_tier",
    "num_projects", "max_project_complexity", "meets_project_complexity",
    "num_global_premium_certs", "num_global_standard_certs",
    "num_national_certs", "meets_cert_tier",
    "num_papers", "max_paper_tier",
    "num_advanced_skills", "num_verified_skills",
]


def load_artifacts():
    """Load classifier model and all data needed for simulation."""
    with open(os.path.join(MODEL_DIR, "model.pkl"),           "rb") as f: model  = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "scaler.pkl"),          "rb") as f: scaler = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "feature_columns.json"))     as f: feat_cols = json.load(f)

    pairs     = pd.read_csv(os.path.join(DATA_DIR, "pair_features.csv"))
    companies = pd.read_csv(os.path.join(DATA_DIR, "companies.csv"))

    # skill_list per student (skill names as CSV string in skills.csv)
    skills_df = pd.read_csv(os.path.join(DATA_DIR, "skills.csv"))
    skill_lists = (
        skills_df.groupby("student_id")["skill_name"]
        .apply(list)
        .reset_index()
        .rename(columns={"skill_name": "skill_list"})
    )
    return model, scaler, feat_cols, pairs, companies, skill_lists


def _compute_skill_match_ratios(skill_list: list[str],
                                 required_str: str,
                                 preferred_str: str) -> tuple[float, float]:
    """Recompute skill match ratios after hypothetically adding a skill."""
    student_lower = [s.lower().strip() for s in skill_list]

    def ratio(skills_str):
        if not skills_str or str(skills_str) == "nan":
            return 1.0
        items = [s.lower().strip() for s in str(skills_str).split(",")]
        if not items:
            return 1.0
        return sum(1 for s in items if s in student_lower) / len(items)

    return ratio(required_str), ratio(preferred_str)


def simulate_student(student_id: str,
                     student_pairs: pd.DataFrame,
                     companies: pd.DataFrame,
                     skill_list: list[str],
                     model,
                     scaler,
                     feat_cols: list[str]) -> list[dict]:
    """
    For one student, compute Δgain for every skill they don't already have.
    Returns list of dicts: {student_id, skill, avg_gain, max_gain, n_companies_gained}
    """
    student_skills_lower = {s.lower().strip() for s in skill_list}

    # Baseline: eligibility probability across all companies
    X_base = student_pairs[feat_cols].fillna(0).values
    baseline_probs = model.predict_proba(scaler.transform(X_base))[:, 1]  # shape (n_companies,)

    candidate_skills = [s for s in ALL_SKILLS if s.lower().strip() not in student_skills_lower]

    rows = []
    for skill in candidate_skills:
        new_skill_list = skill_list + [skill]

        # Recompute feature rows with new skill
        modified_pairs = student_pairs.copy()
        for i, (_, comp_row) in enumerate(companies.iterrows()):
            req_ratio, pref_ratio = _compute_skill_match_ratios(
                new_skill_list,
                comp_row["required_skills"],
                comp_row["preferred_skills"],
            )
            # Only update skill match columns; everything else is unchanged
            idx = modified_pairs.index[i] if i < len(modified_pairs) else None
            if idx is not None:
                modified_pairs.at[idx, "required_skills_match_ratio"]  = round(req_ratio, 3)
                modified_pairs.at[idx, "preferred_skills_match_ratio"] = round(pref_ratio, 3)

        X_mod = modified_pairs[feat_cols].fillna(0).values
        new_probs = model.predict_proba(scaler.transform(X_mod))[:, 1]

        delta = new_probs - baseline_probs
        avg_gain  = float(np.mean(delta))
        max_gain  = float(np.max(delta))
        n_gained  = int(np.sum(delta > 0.01))   # companies where gain > 1%

        rows.append({
            "student_id":           student_id,
            "candidate_skill":      skill,
            "avg_eligibility_gain": round(avg_gain,  4),
            "max_eligibility_gain": round(max_gain,  4),
            "n_companies_gained":   n_gained,
            "baseline_avg_prob":    round(float(np.mean(baseline_probs)), 4),
            "n_skills_currently":   len(skill_list),
        })

    return rows


def run_simulation(max_students: int | None = None,
                   output_path: str | None = None) -> pd.DataFrame:
    """
    Run counterfactual skill simulation for all (or max_students) students.
    Writes data/skill_gap_labels.csv and returns the DataFrame.
    """
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "skill_gap_labels.csv")

    print("=" * 60)
    print("  Option 2 — Skill Gap Simulation")
    print("=" * 60)

    model, scaler, feat_cols, pairs, companies, skill_lists = load_artifacts()

    student_ids = pairs["student_id"].unique()
    if max_students is not None:
        student_ids = student_ids[:max_students]

    # Map company rows in the same order as they appear in pairs (per student)
    company_order = pairs[["company_id"]].drop_duplicates().reset_index(drop=True)
    companies_ordered = company_order.merge(companies, on="company_id")

    all_rows = []
    print(f"\n⚙️   Simulating {len(student_ids)} students × "
          f"{len(ALL_SKILLS)} skills × {len(companies_ordered)} companies …")
    print("    (This may take several minutes for the full dataset)\n")

    skill_list_map = {
        row["student_id"]: row["skill_list"]
        for _, row in skill_lists.iterrows()
    }

    for sid in tqdm(student_ids, desc="Students", unit="student"):
        student_pairs = pairs[pairs["student_id"] == sid].copy().reset_index(drop=True)
        if len(student_pairs) == 0:
            continue
        sl = skill_list_map.get(sid, [])
        rows = simulate_student(
            student_id=sid,
            student_pairs=student_pairs,
            companies=companies_ordered,
            skill_list=sl,
            model=model,
            scaler=scaler,
            feat_cols=feat_cols,
        )
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df.to_csv(output_path, index=False)

    print(f"\n✅  Skill gap labels saved → {output_path}")
    print(f"   Rows:    {len(df):,}")
    print(f"   Students:{df['student_id'].nunique()}")
    print(f"   Skills:  {df['candidate_skill'].nunique()}")
    print(f"   Top gain: {df['avg_eligibility_gain'].max():.4f}")
    return df


if __name__ == "__main__":
    # Quick test: 50 students only (remove limit for full run)
    run_simulation(max_students=50)
