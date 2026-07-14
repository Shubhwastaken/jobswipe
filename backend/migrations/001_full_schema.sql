-- 001_full_schema.sql
-- Full public schema of the production (NEW) database, generated from the live
-- catalog via pg_dump --schema-only and rewritten to be idempotent.
-- Runnable against an empty Postgres database; safe to re-run (IF NOT EXISTS /
-- duplicate-tolerant constraint blocks). Contains NO data and NO credentials.
-- Regenerate after any schema change so a clean clone can reproduce the DB.

CREATE SCHEMA IF NOT EXISTS public;

COMMENT ON SCHEMA public IS 'standard public schema';

CREATE OR REPLACE FUNCTION public.rls_auto_enable() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$$;

CREATE TABLE IF NOT EXISTS public.applications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id text NOT NULL,
    job_id uuid NOT NULL,
    current_status text DEFAULT 'Applied'::text,
    round_results jsonb DEFAULT '{}'::jsonb,
    applied_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.bias_recommendations (
    id bigint NOT NULL,
    company_id text,
    criterion text NOT NULL,
    current_threshold jsonb,
    recommended_threshold jsonb,
    current_disparity double precision,
    projected_disparity double precision,
    current_pool_size integer,
    projected_pool_size integer,
    status text DEFAULT 'proposed'::text,
    recommendation_type text DEFAULT 'threshold'::text,
    simulation_payload jsonb,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.certifications (
    cert_id text NOT NULL,
    student_id text,
    cert_name text NOT NULL,
    issuing_body text,
    tier text,
    domain text,
    year_obtained integer
);

CREATE TABLE IF NOT EXISTS public.companies (
    company_id text NOT NULL,
    company_name text NOT NULL,
    industry text,
    tier text,
    min_cgpa double precision,
    min_10th double precision,
    min_12th double precision,
    max_active_backlogs integer DEFAULT 0,
    allowed_departments text,
    required_skills text,
    preferred_skills text,
    min_internship_months double precision DEFAULT 0,
    internship_tier_preference text DEFAULT 'Any'::text,
    min_projects integer DEFAULT 0,
    project_complexity_min text DEFAULT 'Basic'::text,
    requires_research_paper boolean DEFAULT false,
    cert_tier_required text DEFAULT 'None'::text,
    role_offered text,
    package_lpa double precision,
    bond_years integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.eligibility_results (
    id integer NOT NULL,
    student_id text,
    company_id text,
    eligible boolean NOT NULL,
    score double precision,
    criteria_breakdown jsonb,
    "timestamp" timestamp with time zone DEFAULT now()
);

CREATE SEQUENCE IF NOT EXISTS public.eligibility_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.eligibility_results_id_seq OWNED BY public.eligibility_results.id;

CREATE TABLE IF NOT EXISTS public.improvement_plans (
    id integer NOT NULL,
    student_id text,
    company_id text,
    suggestions jsonb,
    "timestamp" timestamp with time zone DEFAULT now()
);

CREATE SEQUENCE IF NOT EXISTS public.improvement_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.improvement_plans_id_seq OWNED BY public.improvement_plans.id;

CREATE TABLE IF NOT EXISTS public.internships (
    internship_id text NOT NULL,
    student_id text,
    company_name text,
    company_tier text,
    role text,
    domain text,
    duration_months double precision,
    stipend boolean DEFAULT false,
    mode text,
    year integer
);

CREATE TABLE IF NOT EXISTS public.interview_feedback (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid,
    overall_summary text DEFAULT ''::text NOT NULL,
    headline_takeaway text DEFAULT ''::text NOT NULL,
    per_question_feedback jsonb DEFAULT '[]'::jsonb NOT NULL,
    recurring_patterns jsonb DEFAULT '[]'::jsonb NOT NULL,
    next_session_suggestion text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.interview_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id text NOT NULL,
    target_role text NOT NULL,
    target_domain text,
    seniority text DEFAULT 'mid'::text NOT NULL,
    interview_stage text DEFAULT 'first_round'::text NOT NULL,
    structured_profile jsonb DEFAULT '{}'::jsonb NOT NULL,
    competency_plan jsonb DEFAULT '{}'::jsonb NOT NULL,
    question_sequence jsonb DEFAULT '[]'::jsonb NOT NULL,
    phase text DEFAULT 'pre_session'::text NOT NULL,
    current_index integer DEFAULT 0 NOT NULL,
    follow_up_used boolean DEFAULT false NOT NULL,
    status text DEFAULT 'pre_session'::text NOT NULL,
    self_rating text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.interview_turns (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid,
    turn_index integer NOT NULL,
    speaker text NOT NULL,
    content text NOT NULL,
    question_ref text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    recruiter_id uuid,
    company_name text,
    role text,
    role_title text,
    industry text,
    location text DEFAULT 'Chennai'::text,
    remote_policy text DEFAULT 'hybrid'::text,
    required_skills jsonb DEFAULT '[]'::jsonb,
    preferred_skills jsonb DEFAULT '[]'::jsonb,
    interview_timeline text,
    mentorship text,
    highlight_line text,
    job_description text,
    careers_url text,
    ctc text,
    package_lpa double precision,
    job_type text,
    selection_rounds jsonb DEFAULT '[]'::jsonb,
    phi_score double precision,
    is_active boolean DEFAULT true,
    allowed_departments jsonb DEFAULT '[]'::jsonb,
    allowed_branches jsonb DEFAULT '[]'::jsonb,
    grad_years_eligible jsonb DEFAULT '[]'::jsonb,
    min_cgpa double precision DEFAULT 0,
    min_10th double precision DEFAULT 0,
    min_12th double precision DEFAULT 0,
    max_active_backlogs integer DEFAULT 999,
    min_internship_months double precision DEFAULT 0,
    min_projects integer DEFAULT 0,
    requires_research_paper boolean DEFAULT false,
    cert_tier_required text DEFAULT 'None'::text,
    bond_years integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    batch_year integer,
    max_backlogs integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.learning_resources (
    id integer NOT NULL,
    skill_name text NOT NULL,
    title text,
    url text,
    resource_type text,
    estimated_hours integer,
    difficulty text,
    duration_hours integer,
    is_free boolean DEFAULT true,
    link text,
    platform text
);

CREATE SEQUENCE IF NOT EXISTS public.learning_resources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.learning_resources_id_seq OWNED BY public.learning_resources.id;

CREATE TABLE IF NOT EXISTS public.matches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id text NOT NULL,
    recruiter_id uuid,
    job_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    matched_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.model_fairness_history (
    id bigint NOT NULL,
    company_id text,
    epsilon double precision NOT NULL,
    accuracy double precision,
    f1 double precision,
    delta_dp double precision,
    delta_eo double precision,
    trained_at timestamp with time zone DEFAULT now(),
    triggered_by text
);

CREATE TABLE IF NOT EXISTS public.projects (
    project_id text NOT NULL,
    student_id text,
    project_title text,
    domain text,
    tech_stack text,
    complexity text,
    team_size text,
    has_deployment boolean DEFAULT false,
    has_github boolean DEFAULT false,
    duration_weeks integer,
    year integer
);

CREATE TABLE IF NOT EXISTS public.recruiter_interest (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    recruiter_id uuid,
    student_id text NOT NULL,
    job_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.recruiter_pass (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    recruiter_id uuid,
    student_id text NOT NULL,
    job_id uuid NOT NULL,
    reason_code text DEFAULT 'selected_stronger_match'::text,
    reason_note text,
    insight_payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.recruiters (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    company_name text,
    company_domain text,
    email text NOT NULL,
    password_hash text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.research_papers (
    paper_id text NOT NULL,
    student_id text,
    title text,
    publication_venue text,
    tier text,
    domain text,
    year_published integer,
    is_first_author boolean DEFAULT false,
    co_authors_count integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.skills (
    id integer NOT NULL,
    student_id text,
    skill_name text NOT NULL,
    proficiency text,
    verified boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS public.skills_graph (
    id integer NOT NULL,
    skill_name text NOT NULL,
    avg_learning_weeks integer DEFAULT 3,
    difficulty_level text DEFAULT 'Intermediate'::text,
    prerequisites jsonb DEFAULT '[]'::jsonb,
    category text,
    industry_demand_score double precision,
    related_skills text[] DEFAULT '{}'::text[]
);

CREATE SEQUENCE IF NOT EXISTS public.skills_graph_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.skills_graph_id_seq OWNED BY public.skills_graph.id;

CREATE SEQUENCE IF NOT EXISTS public.skills_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.skills_id_seq OWNED BY public.skills.id;

CREATE TABLE IF NOT EXISTS public.student_interest (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id text NOT NULL,
    job_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.student_pass (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id text NOT NULL,
    job_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.students (
    student_id text NOT NULL,
    full_name text NOT NULL,
    gender text,
    department text NOT NULL,
    "10th_marks" double precision,
    "10th_board" text,
    "12th_marks" double precision,
    "12th_board" text,
    cgpa double precision,
    backlogs_history integer DEFAULT 0,
    active_backlogs integer DEFAULT 0,
    year_of_study integer,
    id text,
    register_number text,
    name text,
    email text,
    password_hash text,
    batch_year integer,
    resume_url text,
    resume_parse_confidence jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    portfolio_url text,
    branch text,
    college_name text
);

ALTER TABLE ONLY public.eligibility_results ALTER COLUMN id SET DEFAULT nextval('public.eligibility_results_id_seq'::regclass);

ALTER TABLE ONLY public.improvement_plans ALTER COLUMN id SET DEFAULT nextval('public.improvement_plans_id_seq'::regclass);

ALTER TABLE ONLY public.learning_resources ALTER COLUMN id SET DEFAULT nextval('public.learning_resources_id_seq'::regclass);

ALTER TABLE ONLY public.skills ALTER COLUMN id SET DEFAULT nextval('public.skills_id_seq'::regclass);

ALTER TABLE ONLY public.skills_graph ALTER COLUMN id SET DEFAULT nextval('public.skills_graph_id_seq'::regclass);

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.applications ADD CONSTRAINT applications_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.applications ADD CONSTRAINT applications_student_id_job_id_key UNIQUE (student_id, job_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.bias_recommendations ADD CONSTRAINT bias_recommendations_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.certifications ADD CONSTRAINT certifications_pkey PRIMARY KEY (cert_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.companies ADD CONSTRAINT companies_pkey PRIMARY KEY (company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.eligibility_results ADD CONSTRAINT eligibility_results_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.eligibility_results ADD CONSTRAINT eligibility_results_student_id_company_id_key UNIQUE (student_id, company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.improvement_plans ADD CONSTRAINT improvement_plans_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.improvement_plans ADD CONSTRAINT improvement_plans_student_id_company_id_key UNIQUE (student_id, company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.internships ADD CONSTRAINT internships_pkey PRIMARY KEY (internship_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.interview_feedback ADD CONSTRAINT interview_feedback_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.interview_feedback ADD CONSTRAINT interview_feedback_session_id_key UNIQUE (session_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.interview_sessions ADD CONSTRAINT interview_sessions_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.interview_turns ADD CONSTRAINT interview_turns_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.jobs ADD CONSTRAINT jobs_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.learning_resources ADD CONSTRAINT learning_resources_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.matches ADD CONSTRAINT matches_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.matches ADD CONSTRAINT matches_student_id_job_id_key UNIQUE (student_id, job_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.model_fairness_history ADD CONSTRAINT model_fairness_history_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.projects ADD CONSTRAINT projects_pkey PRIMARY KEY (project_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiter_interest ADD CONSTRAINT recruiter_interest_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiter_interest ADD CONSTRAINT recruiter_interest_student_id_job_id_recruiter_id_key UNIQUE (student_id, job_id, recruiter_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiter_pass ADD CONSTRAINT recruiter_pass_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiter_pass ADD CONSTRAINT recruiter_pass_student_id_job_id_recruiter_id_key UNIQUE (student_id, job_id, recruiter_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiters ADD CONSTRAINT recruiters_email_key UNIQUE (email)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiters ADD CONSTRAINT recruiters_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.research_papers ADD CONSTRAINT research_papers_pkey PRIMARY KEY (paper_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.skills_graph ADD CONSTRAINT skills_graph_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.skills_graph ADD CONSTRAINT skills_graph_skill_name_key UNIQUE (skill_name)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.skills ADD CONSTRAINT skills_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.student_interest ADD CONSTRAINT student_interest_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.student_interest ADD CONSTRAINT student_interest_student_id_job_id_key UNIQUE (student_id, job_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.student_pass ADD CONSTRAINT student_pass_pkey PRIMARY KEY (id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.student_pass ADD CONSTRAINT student_pass_student_id_job_id_key UNIQUE (student_id, job_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.students ADD CONSTRAINT students_pkey PRIMARY KEY (student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_applications_jid ON public.applications USING btree (job_id);

CREATE INDEX IF NOT EXISTS idx_applications_sid ON public.applications USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_bias_recommendations_company ON public.bias_recommendations USING btree (company_id);

CREATE INDEX IF NOT EXISTS idx_certs_student ON public.certifications USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_eligibility_company ON public.eligibility_results USING btree (company_id);

CREATE INDEX IF NOT EXISTS idx_eligibility_student ON public.eligibility_results USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_fairness_history_company ON public.model_fairness_history USING btree (company_id);

CREATE INDEX IF NOT EXISTS idx_improvement_student ON public.improvement_plans USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_internships_student ON public.internships USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_student ON public.interview_sessions USING btree (student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_interview_turns_session ON public.interview_turns USING btree (session_id, turn_index);

CREATE INDEX IF NOT EXISTS idx_jobs_active ON public.jobs USING btree (is_active);

CREATE INDEX IF NOT EXISTS idx_jobs_recruiter ON public.jobs USING btree (recruiter_id);

CREATE INDEX IF NOT EXISTS idx_learning_resources_skill ON public.learning_resources USING btree (skill_name);

CREATE INDEX IF NOT EXISTS idx_matches_jid ON public.matches USING btree (job_id);

CREATE INDEX IF NOT EXISTS idx_matches_sid ON public.matches USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_papers_student ON public.research_papers USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_projects_student ON public.projects USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_recruiter_interest_rid ON public.recruiter_interest USING btree (recruiter_id);

CREATE INDEX IF NOT EXISTS idx_recruiter_interest_sid ON public.recruiter_interest USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_recruiter_pass_created ON public.recruiter_pass USING btree (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_recruiter_pass_sid ON public.recruiter_pass USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_recruiters_email ON public.recruiters USING btree (email);

CREATE INDEX IF NOT EXISTS idx_skills_student ON public.skills USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_student_interest_jid ON public.student_interest USING btree (job_id);

CREATE INDEX IF NOT EXISTS idx_student_interest_sid ON public.student_interest USING btree (student_id);

CREATE INDEX IF NOT EXISTS idx_student_pass_sid ON public.student_pass USING btree (student_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_students_email ON public.students USING btree (email) WHERE (email IS NOT NULL);

CREATE UNIQUE INDEX IF NOT EXISTS idx_students_register ON public.students USING btree (register_number) WHERE (register_number IS NOT NULL);

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.bias_recommendations ADD CONSTRAINT bias_recommendations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.certifications ADD CONSTRAINT certifications_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.eligibility_results ADD CONSTRAINT eligibility_results_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.eligibility_results ADD CONSTRAINT eligibility_results_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.improvement_plans ADD CONSTRAINT improvement_plans_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.improvement_plans ADD CONSTRAINT improvement_plans_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.internships ADD CONSTRAINT internships_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.interview_feedback ADD CONSTRAINT interview_feedback_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.interview_sessions(id) ON DELETE CASCADE';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.interview_turns ADD CONSTRAINT interview_turns_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.interview_sessions(id) ON DELETE CASCADE';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.jobs ADD CONSTRAINT jobs_recruiter_id_fkey FOREIGN KEY (recruiter_id) REFERENCES public.recruiters(id) ON DELETE SET NULL';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.matches ADD CONSTRAINT matches_recruiter_id_fkey FOREIGN KEY (recruiter_id) REFERENCES public.recruiters(id) ON DELETE SET NULL';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.model_fairness_history ADD CONSTRAINT model_fairness_history_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.projects ADD CONSTRAINT projects_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiter_interest ADD CONSTRAINT recruiter_interest_recruiter_id_fkey FOREIGN KEY (recruiter_id) REFERENCES public.recruiters(id) ON DELETE CASCADE';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.recruiter_pass ADD CONSTRAINT recruiter_pass_recruiter_id_fkey FOREIGN KEY (recruiter_id) REFERENCES public.recruiters(id) ON DELETE SET NULL';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.research_papers ADD CONSTRAINT research_papers_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

DO $$ BEGIN
    EXECUTE 'ALTER TABLE ONLY public.skills ADD CONSTRAINT skills_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(student_id)';
EXCEPTION WHEN duplicate_object OR duplicate_table THEN NULL; END $$;

CREATE POLICY "Allow all interview_feedback" ON public.interview_feedback USING (true) WITH CHECK (true);

CREATE POLICY "Allow all interview_sessions" ON public.interview_sessions USING (true) WITH CHECK (true);

CREATE POLICY "Allow all interview_turns" ON public.interview_turns USING (true) WITH CHECK (true);

ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.bias_recommendations ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.certifications ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.eligibility_results ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.improvement_plans ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.internships ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.interview_feedback ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.interview_sessions ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.interview_turns ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.learning_resources ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.model_fairness_history ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.recruiter_interest ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.recruiter_pass ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.recruiters ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.research_papers ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.skills ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.skills_graph ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.student_interest ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.student_pass ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
