"""
Rank Train — Option 1: Learning-to-Rank

Trains an XGBoost ranker with the rank:ndcg objective on (student, company)
pairs.  Each company is a query group; the model learns to order students by
placement fitness, not just classify them as eligible/ineligible.

Key design choices
──────────────────
• rank:ndcg  objective  → directly optimises NDCG, the standard ranking metric
• group array           → tells XGBoost which rows belong to the same query
• StandardScaler        → same preprocessing as the classifier pipeline
• Model artifact        → saved as ranker.pkl alongside the existing model.pkl
"""

import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")

# Same 20 bias-free features as the classifier
FEATURE_COLS = [
    "cgpa_normalized",
    "10th_normalized",
    "12th_normalized",
    "active_backlogs",
    "dept_match",
    "required_skills_match_ratio",
    "preferred_skills_match_ratio",
    "total_internship_months",
    "max_internship_tier",
    "num_projects",
    "max_project_complexity",
    "meets_project_complexity",
    "num_global_premium_certs",
    "num_global_standard_certs",
    "num_national_certs",
    "meets_cert_tier",
    "num_papers",
    "max_paper_tier",
    "num_advanced_skills",
    "num_verified_skills",
]


def load_ranking_data():
    """Load pair features merged with ranking labels."""
    pairs  = pd.read_csv(os.path.join(DATA_DIR, "pair_features.csv"))
    labels = pd.read_csv(os.path.join(DATA_DIR, "ranking_labels.csv"))

    data = pairs.merge(
        labels[["student_id", "company_id", "group_id",
                "fit_score", "relevance_grade", "rank_within_group"]],
        on=["student_id", "company_id"],
    )
    # Sort by group so XGBoost group array is contiguous
    data = data.sort_values("group_id").reset_index(drop=True)
    return data


def build_group_array(data: pd.DataFrame) -> np.ndarray:
    """Return group sizes array required by XGBoost ranker."""
    return data.groupby("group_id", sort=True).size().values


def train_ranker(data: pd.DataFrame,
                 test_ratio: float = 0.20,
                 random_state: int = 42):
    """
    Train XGBoost ranker. Uses GroupShuffleSplit so all pairs of the
    same company land in either train or test — never split across both.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    X = data[FEATURE_COLS].fillna(0)
    y = data["relevance_grade"].values          # 0-3 ordinal relevance
    groups = data["group_id"].values

    # Group-aware train/test split
    gss = GroupShuffleSplit(n_splits=1, test_size=test_ratio, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx],      y[test_idx]
    g_train         = data.iloc[train_idx]["group_id"].values
    g_test          = data.iloc[test_idx]["group_id"].values

    # Scale
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # Group size arrays (must match sorted order)
    train_data_sorted = data.iloc[train_idx].sort_values("group_id")
    test_data_sorted  = data.iloc[test_idx].sort_values("group_id")

    # Re-align after sort
    train_sort_idx = train_data_sorted.index
    test_sort_idx  = test_data_sorted.index

    X_train_s = scaler.transform(X.loc[train_sort_idx].fillna(0))
    y_train   = data.loc[train_sort_idx, "relevance_grade"].values
    X_test_s  = scaler.transform(X.loc[test_sort_idx].fillna(0))
    y_test    = data.loc[test_sort_idx,  "relevance_grade"].values

    group_train = build_group_array(data.loc[train_sort_idx])
    group_test  = build_group_array(data.loc[test_sort_idx])

    if not HAS_XGB:
        raise ImportError("XGBoost is required for rank training. "
                          "Install it with: pip install xgboost")

    print("🚀  Training XGBoost ranker (rank:ndcg) …")
    ranker = xgb.XGBRanker(
        objective="rank:ndcg",
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=random_state,
        tree_method="hist",
        eval_metric="ndcg@10",
    )
    ranker.fit(
        X_train_s, y_train,
        group=group_train,
        eval_set=[(X_test_s, y_test)],
        eval_group=[group_test],
        verbose=False,
    )

    # ── Evaluation ──────────────────────────────────────────────────────────
    scores = ranker.predict(X_test_s)

    # Attach predictions back to test rows for per-group metric computation
    test_df = data.loc[test_sort_idx].copy()
    test_df["pred_score"] = scores
    test_df["true_grade"] = y_test

    metrics = evaluate_ranker(test_df)

    print("\n📊  Ranking Metrics (test set):")
    for k, v in metrics.items():
        print(f"   {k:30s}: {v:.4f}")

    # Feature importance
    importance = ranker.feature_importances_
    feat_imp = sorted(zip(FEATURE_COLS, importance), key=lambda x: x[1], reverse=True)
    print("\n🔍  Feature Importance (top 10):")
    for feat, imp in feat_imp[:10]:
        print(f"   {feat:40s} {imp:.4f}")

    # ── Save artifacts ───────────────────────────────────────────────────────
    ranker_path  = os.path.join(MODEL_DIR, "ranker.pkl")
    rscaler_path = os.path.join(MODEL_DIR, "ranker_scaler.pkl")
    rfeats_path  = os.path.join(MODEL_DIR, "ranker_feature_columns.json")
    rmetrics_path = os.path.join(MODEL_DIR, "ranker_metrics.json")

    with open(ranker_path,  "wb") as f: pickle.dump(ranker,  f)
    with open(rscaler_path, "wb") as f: pickle.dump(scaler,  f)
    with open(rfeats_path,  "w")  as f: json.dump(FEATURE_COLS, f, indent=2)
    with open(rmetrics_path, "w") as f: json.dump(metrics, f, indent=2)

    print(f"\n💾  Ranker saved    → {ranker_path}")
    print(f"💾  Scaler saved    → {rscaler_path}")
    print(f"💾  Metrics saved   → {rmetrics_path}")

    return ranker, scaler, metrics


# ── NDCG utilities ────────────────────────────────────────────────────────────

def dcg_at_k(relevances: np.ndarray, k: int) -> float:
    """Discounted Cumulative Gain at k."""
    r = np.asarray(relevances, dtype=float)[:k]
    if r.size == 0:
        return 0.0
    discounts = np.log2(np.arange(2, r.size + 2))
    return float(np.sum((2 ** r - 1) / discounts))


def ndcg_at_k(relevances: np.ndarray, k: int) -> float:
    """Normalised DCG at k."""
    ideal = dcg_at_k(np.sort(relevances)[::-1], k)
    if ideal == 0:
        return 1.0
    return dcg_at_k(relevances, k) / ideal


def precision_at_k(relevances: np.ndarray, k: int, threshold: int = 1) -> float:
    """Fraction of top-k with relevance ≥ threshold."""
    top_k = np.asarray(relevances)[:k]
    return float(np.mean(top_k >= threshold))


def evaluate_ranker(test_df: pd.DataFrame) -> dict:
    """
    Compute per-group ranking metrics then macro-average across companies.
    """
    ndcg5_list, ndcg10_list, p5_list, p10_list = [], [], [], []

    for _, grp in test_df.groupby("company_id"):
        grp_sorted = grp.sort_values("pred_score", ascending=False)
        rel = grp_sorted["true_grade"].values

        ndcg5_list.append(ndcg_at_k(rel, 5))
        ndcg10_list.append(ndcg_at_k(rel, 10))
        p5_list.append(precision_at_k(rel, 5))
        p10_list.append(precision_at_k(rel, 10))

    return {
        "ndcg@5":       float(np.mean(ndcg5_list)),
        "ndcg@10":      float(np.mean(ndcg10_list)),
        "precision@5":  float(np.mean(p5_list)),
        "precision@10": float(np.mean(p10_list)),
        "num_queries":  int(len(ndcg5_list)),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  Option 1 — XGBoost Learning-to-Rank Training")
    print("=" * 60)

    data = load_ranking_data()
    print(f"\n📂  Loaded {len(data):,} pairs across {data['group_id'].nunique()} companies")

    ranker, scaler, metrics = train_ranker(data)
    print("\n✅  Training complete.")
