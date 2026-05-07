"""
Rank Label Generator — Option 1: Learning-to-Rank

Generates continuous fit scores (0–1) per (student, company) pair using
weighted soft criteria. These replace binary eligible/ineligible labels with
a ranking signal that XGBoost's rank:ndcg objective can optimise.

Score components (weights sum to 1.0):
    required_skills_match    0.25
    preferred_skills_match   0.10
    internship_duration      0.15
    internship_tier          0.05
    project_count            0.10
    project_complexity       0.10
    cert_tier                0.10
    research_papers          0.05
    advanced_skills          0.05
    verified_skills          0.05
"""

import os
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Weight configuration — must sum to 1.0
SCORE_WEIGHTS = {
    "required_skills":  0.25,
    "preferred_skills": 0.10,
    "intern_duration":  0.15,
    "intern_tier":      0.05,
    "num_projects":     0.10,
    "proj_complexity":  0.10,
    "cert_tier":        0.10,
    "papers":           0.05,
    "adv_skills":       0.05,
    "verified_skills":  0.05,
}
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"

# Normalisation caps (domain knowledge)
INTERN_MONTHS_CAP = 6.0   # 6 months == full credit
PROJECT_COUNT_CAP = 4.0   # 4 projects == full credit
PAPERS_CAP        = 2.0   # 2 papers == full credit
ADV_SKILLS_CAP    = 3.0   # 3 advanced skills == full credit
VERIFIED_SKILLS_CAP = 4.0 # 4 verified skills == full credit
MAX_INTERN_TIER   = 5.0   # Tier1 == 5
MAX_CERT_TIER     = 4.0   # Global_Premium == 4
MAX_PROJ_COMPLEXITY = 3.0 # Advanced == 3


def compute_fit_score(row: pd.Series) -> float:
    """
    Compute a continuous fit score in [0, 1] for one (student, company) pair.
    Uses only columns present in pair_features.csv.
    """
    w = SCORE_WEIGHTS

    req_skill_score  = row["required_skills_match_ratio"]
    pref_skill_score = row["preferred_skills_match_ratio"]

    intern_dur_score  = min(row["total_internship_months"] / INTERN_MONTHS_CAP, 1.0)
    intern_tier_score = min(row["max_internship_tier"] / MAX_INTERN_TIER, 1.0)

    proj_count_score = min(row["num_projects"] / PROJECT_COUNT_CAP, 1.0)

    company_req_complexity = row.get("company_complexity_min_encoded", 0)
    student_complexity     = row["max_project_complexity"]
    if company_req_complexity > 0:
        proj_complexity_score = min(student_complexity / company_req_complexity, 1.0)
    else:
        proj_complexity_score = min(student_complexity / MAX_PROJ_COMPLEXITY, 1.0)

    # Cert score: meets_cert_tier (binary) + premium certs bonus
    meets_cert   = float(row.get("meets_cert_tier", 0))
    premium_bonus = min(row.get("num_global_premium_certs", 0) / 2.0, 0.5)
    cert_score   = min(meets_cert * 0.7 + premium_bonus, 1.0)

    paper_score  = min(row["num_papers"] / PAPERS_CAP, 1.0)
    adv_score    = min(row["num_advanced_skills"] / ADV_SKILLS_CAP, 1.0)
    ver_score    = min(row["num_verified_skills"] / VERIFIED_SKILLS_CAP, 1.0)

    score = (
        w["required_skills"]  * req_skill_score  +
        w["preferred_skills"] * pref_skill_score +
        w["intern_duration"]  * intern_dur_score  +
        w["intern_tier"]      * intern_tier_score +
        w["num_projects"]     * proj_count_score  +
        w["proj_complexity"]  * proj_complexity_score +
        w["cert_tier"]        * cert_score        +
        w["papers"]           * paper_score       +
        w["adv_skills"]       * adv_score         +
        w["verified_skills"]  * ver_score
    )
    return round(float(np.clip(score, 0.0, 1.0)), 4)


def generate_rank_labels(pairs_path: str | None = None,
                          labels_path: str | None = None,
                          output_path: str | None = None) -> pd.DataFrame:
    """
    Load pair features + existing labels, compute fit scores, and write
    ranking_labels.csv with columns:
        student_id, company_id, group_id (== company ordinal),
        fit_score, rank_within_group, eligible (from Layer-1 hard pass)
    """
    if pairs_path is None:
        pairs_path = os.path.join(DATA_DIR, "pair_features.csv")
    if labels_path is None:
        labels_path = os.path.join(DATA_DIR, "training_labels.csv")
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "ranking_labels.csv")

    print("📂  Loading pair features and training labels …")
    pairs  = pd.read_csv(pairs_path)
    labels = pd.read_csv(labels_path)[["student_id", "company_id", "eligible", "hard_pass"]]
    companies = pd.read_csv(os.path.join(DATA_DIR, "companies.csv"))

    # Merge hard_pass eligibility
    df = pairs.merge(labels, on=["student_id", "company_id"], how="left")

    # Merge company complexity so fit_score can use it
    comp_complexity_map = {"None": 0, "Basic": 1, "Intermediate": 2, "Advanced": 3}
    companies["company_complexity_min_encoded"] = companies["project_complexity_min"].map(
        comp_complexity_map).fillna(0)
    df = df.merge(
        companies[["company_id", "company_complexity_min_encoded"]],
        on="company_id", how="left"
    )
    df["company_complexity_min_encoded"] = df["company_complexity_min_encoded"].fillna(0)

    print(f"   → {len(df):,} (student × company) pairs loaded")

    # Compute continuous fit score
    print("⚙️   Computing fit scores …")
    df["fit_score"] = df.apply(compute_fit_score, axis=1)

    # Hard-gate: ineligible students get score 0 (they fail Layer 1)
    df.loc[df["hard_pass"] == 0, "fit_score"] = 0.0

    # Assign group_id (each company = one query group for LTR)
    company_order = {cid: idx for idx, cid in enumerate(sorted(df["company_id"].unique()))}
    df["group_id"] = df["company_id"].map(company_order)

    # Rank within each company group (1 = best)
    df["rank_within_group"] = df.groupby("company_id")["fit_score"].rank(
        ascending=False, method="min"
    ).astype(int)

    # Relevance grade for NDCG (0–3 scale, used by XGBoost rank:ndcg)
    # grade 3 = top quartile, 2 = second, 1 = third, 0 = ineligible/bottom
    df["relevance_grade"] = 0
    eligible_mask = df["hard_pass"] == 1
    q75 = df.loc[eligible_mask, "fit_score"].quantile(0.75)
    q50 = df.loc[eligible_mask, "fit_score"].quantile(0.50)
    q25 = df.loc[eligible_mask, "fit_score"].quantile(0.25)

    df.loc[eligible_mask & (df["fit_score"] >= q75), "relevance_grade"] = 3
    df.loc[eligible_mask & (df["fit_score"] >= q50) & (df["fit_score"] < q75), "relevance_grade"] = 2
    df.loc[eligible_mask & (df["fit_score"] >= q25) & (df["fit_score"] < q50), "relevance_grade"] = 1

    # Final output columns
    out_cols = [
        "student_id", "company_id", "group_id",
        "fit_score", "relevance_grade", "rank_within_group",
        "eligible", "hard_pass",
    ]
    result = df[out_cols].sort_values(["company_id", "rank_within_group"])

    result.to_csv(output_path, index=False)
    print(f"\n✅  Ranking labels saved → {output_path}")
    print(f"   Pairs:         {len(result):,}")
    print(f"   Eligible:      {result['eligible'].sum():,} ({result['eligible'].mean()*100:.1f}%)")
    print(f"   Score range:   [{result['fit_score'].min():.4f}, {result['fit_score'].max():.4f}]")
    print(f"   Grade dist:    {dict(result['relevance_grade'].value_counts().sort_index())}")
    print(f"   Companies:     {result['company_id'].nunique()}")
    print(f"   Students:      {result['student_id'].nunique()}")
    return result


if __name__ == "__main__":
    generate_rank_labels()
