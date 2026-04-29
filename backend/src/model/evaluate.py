"""
Model Evaluation: Comprehensive metrics and analysis.
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix,
    precision_recall_curve, roc_curve
)
from sklearn.model_selection import cross_val_score

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'models')


def evaluate_model():
    """Run comprehensive model evaluation."""
    with open(os.path.join(MODEL_DIR, "model.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "feature_columns.json"), "r") as f:
        feature_cols = json.load(f)

    pairs = pd.read_csv(os.path.join(DATA_DIR, "pair_features.csv"))
    labels = pd.read_csv(os.path.join(DATA_DIR, "training_labels.csv"))

    data = pairs.merge(labels[["student_id", "company_id", "eligible"]],
                       on=["student_id", "company_id"])

    X = data[feature_cols].fillna(0)
    y = data["eligible"]
    X_scaled = scaler.transform(X)

    y_pred = model.predict(X_scaled)
    y_proba = model.predict_proba(X_scaled)[:, 1]

    print("=" * 60)
    print("  📊 Full Model Evaluation Report")
    print("=" * 60)

    # Basic metrics
    print(f"\n  Accuracy:  {accuracy_score(y, y_pred):.4f}")
    print(f"  Precision: {precision_score(y, y_pred, zero_division=0):.4f}")
    print(f"  Recall:    {recall_score(y, y_pred, zero_division=0):.4f}")
    print(f"  F1 Score:  {f1_score(y, y_pred, zero_division=0):.4f}")
    print(f"  ROC AUC:   {roc_auc_score(y, y_proba):.4f}")

    print("\n📋 Classification Report:")
    print(classification_report(y, y_pred, target_names=["Ineligible", "Eligible"]))

    print("📊 Confusion Matrix:")
    cm = confusion_matrix(y, y_pred)
    print(f"  Predicted:    Ineligible  Eligible")
    print(f"  Actual Inelig:   {cm[0][0]:6d}    {cm[0][1]:6d}")
    print(f"  Actual Elig:     {cm[1][0]:6d}    {cm[1][1]:6d}")

    # Cross-validation
    print("\n🔄 5-Fold Cross-Validation:")
    cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='f1')
    print(f"  F1 scores: {[f'{s:.4f}' for s in cv_scores]}")
    print(f"  Mean F1:   {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Score distribution
    print("\n📈 Score Distribution:")
    for threshold in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        eligible_count = (y_proba >= threshold).sum()
        print(f"  Score >= {threshold}: {eligible_count} ({eligible_count/len(y_proba)*100:.1f}%)")

    # Save evaluation report
    eval_report = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "f1": float(f1_score(y, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, y_proba)),
        "cv_f1_mean": float(cv_scores.mean()),
        "cv_f1_std": float(cv_scores.std()),
        "total_samples": len(y),
        "positive_rate": float(y.mean()),
    }

    eval_path = os.path.join(MODEL_DIR, "evaluation_report.json")
    with open(eval_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"\n💾 Evaluation report saved → {eval_path}")

    return eval_report


if __name__ == "__main__":
    evaluate_model()
