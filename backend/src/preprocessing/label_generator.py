"""
Label Generator: Generate training labels based on CRITERIA RULES, not historical data.
This is the key anti-bias mechanism — labels come from transparent rules,
not from biased past placement decisions.
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


def generate_labels(pair_features_path=None):
    """
    For each (student, company) pair, generate a binary label:
      1 = eligible (all hard checks pass AND soft score > threshold)
      0 = ineligible

    Also generates a continuous 'criteria_score' for ranking.
    """
    if pair_features_path is None:
        pair_features_path = os.path.join(DATA_DIR, "pair_features.csv")

    companies = pd.read_csv(os.path.join(DATA_DIR, "companies.csv"))
    pairs = pd.read_csv(pair_features_path)

    # Merge company requirements into pairs
    pairs = pairs.merge(
        companies[["company_id", "min_cgpa", "min_10th", "min_12th",
                    "max_active_backlogs", "min_internship_months",
                    "min_projects", "requires_research_paper"]],
        on="company_id",
        how="left"
    )

    # === HARD DISQUALIFIERS ===
    # Any one failing = ineligible, regardless of everything else
    pairs["hard_cgpa"] = (pairs["cgpa_normalized"] * 10 >= pairs["min_cgpa"]).astype(int)
    pairs["hard_10th"] = (pairs["10th_normalized"] * 100 >= pairs["min_10th"]).astype(int)
    pairs["hard_12th"] = (pairs["12th_normalized"] * 100 >= pairs["min_12th"]).astype(int)
    pairs["hard_backlogs"] = (pairs["active_backlogs"] <= pairs["max_active_backlogs"]).astype(int)
    pairs["hard_dept"] = pairs["dept_match"]

    # All hard checks must pass
    pairs["hard_pass"] = (
        pairs["hard_cgpa"] &
        pairs["hard_10th"] &
        pairs["hard_12th"] &
        pairs["hard_backlogs"] &
        pairs["hard_dept"]
    ).astype(int)

    # === SOFT SCORING (for ranking among eligible candidates) ===
    # Weighted sum of soft criteria
    pairs["soft_score"] = (
        pairs["required_skills_match_ratio"] * 0.25 +
        pairs["preferred_skills_match_ratio"] * 0.10 +
        np.minimum(pairs["total_internship_months"] / 6.0, 1.0) * 0.15 +
        np.minimum(pairs["max_internship_tier"] / 5.0, 1.0) * 0.05 +
        np.minimum(pairs["num_projects"] / 4.0, 1.0) * 0.10 +
        pairs["meets_project_complexity"] * 0.10 +
        pairs["meets_cert_tier"] * 0.10 +
        np.minimum(pairs["num_papers"] / 2.0, 1.0) * 0.05 +
        np.minimum(pairs["num_advanced_skills"] / 3.0, 1.0) * 0.05 +
        np.minimum(pairs["num_verified_skills"] / 4.0, 1.0) * 0.05
    )

    # Clip to [0, 1]
    pairs["soft_score"] = pairs["soft_score"].clip(0, 1)

    # === LABEL GENERATION ===
    # Eligible = hard checks pass AND soft score above threshold
    SOFT_THRESHOLD = 0.35

    # Add small controlled noise to prevent cliff effects
    noise = np.random.RandomState(42).normal(0, 0.03, len(pairs))
    pairs["noisy_soft"] = (pairs["soft_score"] + noise).clip(0, 1)

    pairs["eligible"] = (
        (pairs["hard_pass"] == 1) &
        (pairs["noisy_soft"] >= SOFT_THRESHOLD)
    ).astype(int)

    # Overall criteria score (for continuous ranking)
    pairs["criteria_score"] = (pairs["hard_pass"] * pairs["soft_score"]).round(4)

    # Keep only needed columns for training
    label_cols = ["student_id", "company_id", "eligible", "criteria_score",
                  "hard_pass", "soft_score"]
    labels = pairs[label_cols].copy()

    # Save
    labels_path = os.path.join(DATA_DIR, "training_labels.csv")
    labels.to_csv(labels_path, index=False)
    print(f"✅ Generated {len(labels)} labels → {labels_path}")
    print(f"   Eligible: {labels['eligible'].sum()} ({labels['eligible'].mean()*100:.1f}%)")
    print(f"   Ineligible: {(1 - labels['eligible']).sum()} ({(1 - labels['eligible']).mean()*100:.1f}%)")

    return labels


if __name__ == "__main__":
    generate_labels()
