# Bias-Free AI Placement Automation: Project Workflow & Phases

This document tracks the entire lifecycle, architecture, and ongoing operations of the Bias-free AI Placement Automation system. Every time the pipeline is executed, it follows these exact phases.

## Phase 1: Synthetic Data Generation
*   **Goal:** Create a 100% historically-unbiased dataset to train the ML pipeline.
*   **Action:** Scripts (`generate_students.py`, `generate_companies.py`, etc.) generate 800 correlated students and 50 companies. 
*   **Result:** Outputs clean CSV files to the `/data` directory. Protected attributes (Name, Gender, Board Type) are generated for the frontend/audit only, never for the model.

## Phase 2: Preprocessing & Feature Engineering
*   **Goal:** Aggregate scattered student tables (projects, internships, certifications) into a single optimized feature vector per candidate-company pair.
*   **Action:** `feature_engineering.py` matches the 800 students against 50 companies (40,000 pairs). It computes domain matching, skill overlaps, and academic thresholds.
*   **Result:** `pair_features.csv` containing the fully numeric, unbiased input matrix.

## Phase 3: Rule-Based Label Generation (The Ground Truth)
*   **Goal:** Create unbiased training labels (`eligible`: True/False) based entirely on transparent programmatic criteria.
*   **Action:** `label_generator.py` evaluates all 40,000 pairs against hard constraints (max backlogs, min CGPA, required skills).
*   **Result:** `training_labels.csv` — typically yielding an ~15-25% eligibility rate without human bias.

## Phase 4: Model Training & Tuning
*   **Goal:** Train an AI ranker (XGBoost/LightGBM/Ensembles/Fairlearn) to softly score candidates who pass or are borderline on the hard criteria.
*   **Action:** Central machine learning pipelines ingest the features and criteria labels. We tune hyperparameters for maximum F1/Accuracy, and apply bias-mitigating techniques to ensure fairness.
*   **Result:** Centralized ML artifacts exported to `/models`.

## Phase 5: Fairness Auditing
*   **Goal:** Mathematically prove the model is unbiased across Demographic Parity and Equalized Odds.
*   **Action:** `fairness_audit.py` checks the ML predictions against the hidden protected attributes (Gender, Department, 10th/12th Board).
*   **Result:** Ensures disparities remain under a strict threshold (<= 10%), rejecting models that fail.

## Phase 6: Explainability & Actionable Feedback
*   **Goal:** Eliminate "black box" rejections.
*   **Action:** `improvement_planner.py` evaluates failed pairs and generates prioritized, human-readable action items for the candidate to improve their chances in the future.

## Phase 7: UI & Systems Integration
*   **Goal:** Expose the pipeline via a robust API and Admin Dashboard.
*   **Action:** FastAPI (`main.py`) serves the endpoints, and the React/Vite frontend displays real-time telemetry, model metrics, and student data logic.

---
*Status: Live & Updating. Advancing into Model Maximization (Phase 4 optimization)...*
