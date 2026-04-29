# JobSwipe - Bias-Free AI Placement Automation

A production-grade, mathematically-fair AI placement automation system. This project models an end-to-end Machine Learning pipeline that scores candidate-company fit while strictly mitigating demographic, department, and social bias.

## 🎯 Key Features & The 7-Phase Workflow

This system is built around a rigorous 7-phase architecture to ensure zero "black box" decisions:

1. **Synthetic Data Generation**: Generates 800 correlated students and 50 companies with hidden protected attributes.
2. **Preprocessing & Feature Engineering**: Reduces categorical and textual data into a purely numeric, unbiased feature matrix.
3. **Rule-Based Labeling**: Establishes ground-truth eligibility using logical constraints (e.g., Backlogs < X, skill matches).
4. **Fairness-Aware Model Training**: Utilizes advanced ML (LightGBM, Ensembles) wrapped in Fairlearn constraints to optimize for Equalized Odds and Demographic Parity.
5. **Fairness Auditing**: Automatically rejects models with > 10% disparity across genders or departments.
6. **Explainable AI (XAI)**: Generates prioritized improvement feedback for rejected candidates.
7. **Systems Integration (Admin UI)**: A premium, dynamic React frontend connecting via FastAPI to serve real-time predictions.

---

## 🚀 Quick Start (Running Locally)

**Prerequisites:** Node.js 18+ and Python 3.9+

### Option A: Automated Startup (Windows)

Use the provided batch scripts to launch both servers simultaneously:

1. Open a terminal and run the backend:
   ```cmd
   double-click run_backend.bat
   ```
2. Open a second terminal and run the frontend:
   ```cmd
   double-click run_frontend.bat
   ```

### Option B: Manual Setup

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Activate the virtual environment
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
> The API will be live at `http://localhost:8000`.

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
> The Admin Dashboard will be live at `http://localhost:3000`.

---

## 💻 The Admin Workspace

The standard student flows have been consolidated into a powerful **Admin Dashboard MVP** for evaluation purposes.

### Core Views:
- **Overview Dashboard (`/dashboard`)**: Monitor AI model accuracy, fairness metrics (Gender & Department Parity), and total applicant distribution.
- **Students Database (`/students`)**: High-level view of all synthesized candidates and their extracted CGPA/skills.
- **Companies Database (`/companies`)**: Active hiring flows, role requirements, and basic hard filters.
- **Eligibility Engine (`/eligibility`)**: The core AI assessment arena.
  - **Single Mode**: Pick a candidate and a company. Execute the pipeline to see explainable scorecard breakdowns.
  - **Batch Mode**: Run the whole 800-candidate pool against a company profile to get a ranked, fairness-adjusted shortlist.

---

## 🛠️ Technology Stack

- **Backend / Pipeline Engine**: FastAPI (Python), Pandas, Scikit-Learn, LightGBM, Fairlearn.
- **Frontend / Telemetry UI**: React 18, Vite, Zustand, TailwindCSS (Vanilla Custom CSS + Glassmorphism UX).
- **Data Mocks**: Faker (Python) to establish mathematically consistent datasets.

---

## 📝 Notes for Evaluators

1. Please evaluate the codebase by navigating through the `/eligibility` engine on the frontend to visualize the real-time interaction between the prediction pipeline and the UI.
2. The UI is built using a custom, animation-rich "Premium Dark" theme without heavy reliance on external UI frameworks to maintain extreme performance and granular style control.
3. Check `project_workflow.md` for a deeper breakdown of the mathematical assumptions behind each phase.

**System Status**: Live & Operational (Phase 4-7 active).

