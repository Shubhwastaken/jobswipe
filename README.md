# JobSwipe

**A swipe-based campus placement platform with fairness-aware AI matching.**

JobSwipe connects students and recruiters through a Tinder-style swipe flow: students swipe
on roles, recruiters swipe on candidates, and a **mutual right-swipe creates a match**.
Behind the swipe is a bias-mitigated machine-learning pipeline that ranks candidate–role fit
while auditing for demographic and departmental disparity, plus explainable feedback so
rejected students know exactly what to improve.

---

## What it does

JobSwipe is a three-sided product:

### 🎓 Students
- Swipe through roles ranked by a fairness-aware match score.
- See mutual matches and recruiter interest.
- Build and parse resumes (AI-assisted) to populate their profile.
- Get **explainable rejection insights** — peer comparison, skill gaps, and a prioritized
  improvement plan instead of a silent "no".

### 🏢 Recruiters
- Post and manage roles.
- Swipe through eligible, ranked candidates for each role.
- Track interest and matches.

### 🛠️ Admin / Placement team
- Overview dashboard for model accuracy and fairness metrics.
- Student and company databases.
- **Eligibility engine** — single or batch criteria + ML assessment with scorecards.
- **ML ranked shortlist** per role.
- **Bias detection & feed-replay** tools to audit and simulate fairer selection rules.

---

## How matching works

1. **Hard eligibility filter** — rule-based criteria (CGPA, backlogs, department, required
   skills) gate who is even shown for a role.
2. **Fairness-aware scoring** — eligible pairs are scored by blending a heuristic
   "TalentForge" matcher with a **Fairlearn-constrained champion model** trained to limit
   gender/department disparity (Demographic Parity / Equalized Odds).
3. **Bias auditing** — the admin tools detect roles whose criteria produce disparate pass
   rates and let the team simulate threshold/criteria substitutions before applying them.
4. **Explainability** — for any rejection, the system generates a scorecard, peer
   benchmark, and a feasibility-weighted improvement plan.

---

## Tech stack

| Layer | Stack |
|-------|-------|
| **Backend / API** | FastAPI (Python), JWT auth |
| **Database** | Postgres (Supabase-hosted) via direct psycopg2 client |
| **ML / pipeline** | pandas, scikit-learn, LightGBM, Fairlearn |
| **AI assist** | Groq (LLM) for resume text generation |
| **Frontend** | React 18, Vite, TypeScript, Zustand, TailwindCSS |

---

## Project structure

```
jobswipe/
├── backend/                # FastAPI service + ML pipeline
│   ├── app/
│   │   ├── routers/        # auth, swipe, profile, resume, resume_builder, ...
│   │   ├── services/       # matcher, bias_reduction, artifact registry, ...
│   │   └── main.py         # app entrypoint + admin-gated API surface
│   ├── src/                # ML pipeline (preprocessing, model, explainability)
│   ├── data/               # datasets
│   ├── models/             # trained model artifacts
│   ├── scripts/            # seed / maintenance scripts
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # React + TypeScript + Vite (Tailwind)
│   └── src/                # components, pages (student/recruiter/admin), services, store
├── supabase/               # SQL schema + migrations
├── start_dev.bat           # launch backend + frontend together (Windows)
├── run_backend.{sh,bat}    # local dev launchers
└── run_frontend.{sh,bat}
```

---

## Quick start

**Prerequisites:** Node.js 18+, Python 3.9+, a Postgres database (e.g. a Supabase
project — see `SUPABASE_SETUP.md` for schema setup and system dependencies).

### Backend
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in the values below (DATABASE_URL is required)
uvicorn app.main:app --reload --port 8000
```
API runs at `http://localhost:8000` (Swagger UI at `/docs`).

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App runs at `http://localhost:3000`.

> Windows users can double-click `start_dev.bat` (launches backend + frontend
> together) or `run_backend.bat` / `run_frontend.bat` individually.

---

## Configuration

All configuration is environment-driven. Never commit real secrets — only `*.env.example`
files (with placeholders) are tracked.

**`backend/.env`**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string (`postgresql://user:pass@host:5432/db`; Supabase: Project Settings → Database) |
| `JWT_SECRET` | Token signing secret (use a long random value) |
| `JWT_TTL_HOURS` | Access-token lifetime (default 12) |
| `CORS_ORIGINS` | Allowed browser origins (default `http://localhost:3000`) |
| `GROQ_API_KEY` | LLM key for resume generation |
| `BACKEND_PORT` | API port (default 8000) |

**`frontend/.env.local`**

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Backend base URL (e.g. `http://127.0.0.1:8000`) |

---

## Security model

- **Auth:** JWT (HS256) with `iat`/`exp` claims; lifetime via `JWT_TTL_HOURS`. The frontend
  clears the session and redirects to login on `401/403`.
- **Roles:** `student`, `recruiter`, `admin`. Per-role endpoints use dependencies in
  `app/routers/deps.py`; student PII, ML, and bias/admin endpoints are served behind an
  **admin-gated router** in `app/main.py`.
- **CORS:** explicit allowlist (no wildcard with credentials).


## Development notes

- Database access goes through `execute_supabase()` in `app/routers/swipe.py`.
- Add new DB changes as timestamped files under `supabase/migrations/`; don't edit applied
  migrations.
- Frontend API calls use the shared axios instance in `src/services/api.ts` (attaches the
  bearer token, handles 401s).
- Before a PR: `cd frontend && npx tsc --noEmit` and `cd backend && python -c "import app.main"`.
- Logs, build output, `venv/`, `node_modules/`, and all markdown except this README are
  git-ignored.
