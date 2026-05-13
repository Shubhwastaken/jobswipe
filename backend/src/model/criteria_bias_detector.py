"""
Criteria Bias Detector — Option 3: Upstream Criteria Fairness Audit

Detects whether a company's own hard criteria inadvertently discriminate
against demographic groups — independently of any ML model.

Method
──────
For each company:
  1. Run Layer-1 hard rule filter on every student
  2. Compute pass rate per gender group
  3. Fisher's Exact Test (gender) + Chi-Square (department)
  4. Flag companies where disparity > 10% AND p < 0.05
  5. Diagnose which specific criterion (CGPA, backlog, dept) drives the bias

Output: models/criteria_bias_report.json + models/criteria_bias_report.csv
"""

import json
import os

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact

try:
    from app.services.data_paths import data_dir, dataset_variant
except Exception:
    data_dir = None
    dataset_variant = None

_HERE     = os.path.dirname(__file__)
DATA_DIR  = str(data_dir()) if data_dir else os.path.join(_HERE, "..", "..", "data")
MODEL_DIR = os.path.join(_HERE, "..", "..", "models")

DISPARITY_THRESHOLD = 0.10
SIGNIFICANCE_LEVEL  = 0.05


def apply_hard_rules(students_df: pd.DataFrame, company: pd.Series) -> pd.Series:
    allowed_depts = [d.strip() for d in str(company["allowed_departments"]).split(",")]
    return (
        (students_df["cgpa"]           >= float(company["min_cgpa"]))      &
        (students_df["10th_marks"]     >= float(company["min_10th"]))       &
        (students_df["12th_marks"]     >= float(company["min_12th"]))       &
        (students_df["active_backlogs"] <= int(company["max_active_backlogs"])) &
        (students_df["department"].isin(allowed_depts))
    )


def gender_fisher(pass_mask: pd.Series, gender_series: pd.Series) -> dict:
    df = pd.DataFrame({"pass": pass_mask.astype(int), "gender": gender_series})
    rates = df.groupby("gender")["pass"].mean().to_dict()
    counts = {g: {"pass": int(grp.sum()), "fail": int((~grp.astype(bool)).sum())}
              for g, grp in df.groupby("gender")["pass"]}
    genders = sorted(counts.keys())
    if len(genders) < 2:
        return {"pass_rates": rates, "disparity": 0.0,
                "odds_ratio": 1.0, "p_value": 1.0,
                "significant": False, "flagged": False}
    g0, g1 = genders[0], genders[1]
    table = [[counts[g0]["pass"], counts[g0]["fail"]],
             [counts[g1]["pass"], counts[g1]["fail"]]]
    min_cell = min(c for row in table for c in row)
    if min_cell < 5:
        odds_ratio, p_value = fisher_exact(table)
    else:
        _, p_value, _, _ = chi2_contingency(table)
        odds_ratio = float("nan")
    rate_vals = list(rates.values())
    disparity = max(rate_vals) - min(rate_vals)
    flagged   = (disparity > DISPARITY_THRESHOLD) and (p_value < SIGNIFICANCE_LEVEL)
    return {
        "pass_rates":  {k: round(v, 4) for k, v in rates.items()},
        "disparity":   round(disparity, 4),
        "odds_ratio":  round(float(odds_ratio), 4) if not np.isnan(odds_ratio) else None,
        "p_value":     round(float(p_value), 6),
        "significant": bool(p_value < SIGNIFICANCE_LEVEL),
        "flagged":     bool(flagged),
    }


def dept_chisq(pass_mask: pd.Series, dept_series: pd.Series) -> dict:
    df = pd.DataFrame({"pass": pass_mask.astype(int), "dept": dept_series})
    ct = pd.crosstab(df["dept"], df["pass"])
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return {"disparity": 0.0, "p_value": 1.0, "significant": False,
                "flagged": False, "pass_rates": {}}
    _, p_value, _, _ = chi2_contingency(ct)
    rates     = df.groupby("dept")["pass"].mean().to_dict()
    rate_vals = list(rates.values())
    disparity = max(rate_vals) - min(rate_vals)
    flagged   = (disparity > DISPARITY_THRESHOLD) and (p_value < SIGNIFICANCE_LEVEL)
    return {
        "pass_rates":  {k: round(v, 4) for k, v in rates.items()},
        "disparity":   round(disparity, 4),
        "p_value":     round(float(p_value), 6),
        "significant": bool(p_value < SIGNIFICANCE_LEVEL),
        "flagged":     bool(flagged),
    }


def diagnose_criteria(students_df: pd.DataFrame, company: pd.Series) -> dict:
    allowed_depts = [d.strip() for d in str(company["allowed_departments"]).split(",")]
    criteria = {
        "cgpa":    students_df["cgpa"]           >= float(company["min_cgpa"]),
        "10th":    students_df["10th_marks"]     >= float(company["min_10th"]),
        "12th":    students_df["12th_marks"]     >= float(company["min_12th"]),
        "backlog": students_df["active_backlogs"] <= int(company["max_active_backlogs"]),
        "dept":    students_df["department"].isin(allowed_depts),
    }
    diag = {}
    for name, col in criteria.items():
        rates = col.groupby(students_df["gender"]).mean().to_dict()
        if len(rates) >= 2:
            vals = list(rates.values())
            diag[name] = {
                "pass_rates": {k: round(v, 4) for k, v in rates.items()},
                "disparity":  round(max(vals) - min(vals), 4),
            }
    return diag


def run_criteria_bias_detection(output_json=None, output_csv=None) -> dict:
    active_variant = dataset_variant() if dataset_variant else "canonical"
    artifact_prefix = "resume_realworld_" if active_variant == "realworld" else ""
    if output_json is None:
        output_json = os.path.join(MODEL_DIR, f"{artifact_prefix}criteria_bias_report.json")
    if output_csv is None:
        output_csv  = os.path.join(MODEL_DIR, f"{artifact_prefix}criteria_bias_report.csv")
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("=" * 60)
    print("  Option 3 — Criteria Bias Detection")
    print("=" * 60)

    students  = pd.read_csv(os.path.join(DATA_DIR, "students.csv"))
    companies = pd.read_csv(os.path.join(DATA_DIR, "companies.csv"))

    gender_pool = students["gender"].value_counts(normalize=True).to_dict()
    print(f"\n📊  Pool: {len(students)} students")
    print(f"    Gender: {', '.join(f'{k}={v:.1%}' for k,v in gender_pool.items())}")

    results, flagged_list, flat_rows = [], [], []

    for _, company in companies.iterrows():
        cid   = company["company_id"]
        cname = company["company_name"]
        tier  = company["tier"]

        pass_mask = apply_hard_rules(students, company)
        ga = gender_fisher(pass_mask, students["gender"])
        da = dept_chisq(pass_mask,   students["department"])
        cd = diagnose_criteria(students, company)

        results.append({
            "company_id": cid, "company_name": cname, "tier": tier,
            "pool_pass_rate": round(float(pass_mask.mean()), 4),
            "gender_analysis": ga, "dept_analysis": da,
            "criteria_diagnosis": cd,
            "flagged_gender_bias": ga["flagged"],
        })

        if ga["flagged"]:
            top_driver = max(cd, key=lambda k: cd[k]["disparity"], default="unknown")
            flagged_list.append({
                "company_id": cid, "company_name": cname, "tier": tier,
                "disparity": ga["disparity"], "p_value": ga["p_value"],
                "pass_rates": ga["pass_rates"], "top_bias_criterion": top_driver,
            })

        flat_rows.append({
            "company_id": cid, "company_name": cname, "tier": tier,
            "pool_pass_rate":           round(float(pass_mask.mean()), 4),
            "gender_disparity":         ga["disparity"],
            "gender_p_value":           ga["p_value"],
            "gender_flagged":           ga["flagged"],
            "dept_disparity":           da["disparity"],
            "dept_p_value":             da["p_value"],
            "dept_flagged":             da["flagged"],
            "cgpa_gender_disparity":    cd.get("cgpa",    {}).get("disparity", 0),
            "backlog_gender_disparity": cd.get("backlog", {}).get("disparity", 0),
            "dept_filter_disparity":    cd.get("dept",    {}).get("disparity", 0),
        })

    n_flagged = len(flagged_list)
    print(f"\n⚠️   {n_flagged} / {len(results)} companies flagged for gender bias")
    print(f"    (disparity > {DISPARITY_THRESHOLD*100:.0f}% AND p < {SIGNIFICANCE_LEVEL})\n")
    print(f"  {'Company':33s} {'Tier':6} {'Disparity':10} {'p-value':10} {'Driver'}")
    print("  " + "-" * 70)
    for f in sorted(flagged_list, key=lambda x: x["disparity"], reverse=True):
        print(f"  {f['company_name']:33s} {f['tier']:6} "
              f"{f['disparity']:9.3f}  {f['p_value']:9.4f}  {f['top_bias_criterion']}")

    report = {
        "summary": {
            "n_companies": len(results), "n_flagged": n_flagged,
            "flag_rate": round(n_flagged / len(results), 4),
            "threshold": DISPARITY_THRESHOLD,
            "significance": SIGNIFICANCE_LEVEL,
            "student_pool_size": len(students),
            "gender_pool_dist": gender_pool,
        },
        "flagged_companies": flagged_list,
        "all_companies":     results,
    }

    def _san(o):
        if isinstance(o, dict):  return {str(k): _san(v) for k, v in o.items()}
        if isinstance(o, list):  return [_san(v) for v in o]
        if isinstance(o, (np.integer,)):  return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.bool_,)):    return bool(o)
        return o

    with open(output_json, "w") as f:
        json.dump(_san(report), f, indent=2)

    flat_df = pd.DataFrame(flat_rows).sort_values("gender_disparity", ascending=False)
    flat_df.to_csv(output_csv, index=False)

    print(f"\n💾  JSON → {output_json}")
    print(f"💾  CSV  → {output_csv}")
    print("\n✅  Option 3 complete.")
    return report


if __name__ == "__main__":
    run_criteria_bias_detection()
