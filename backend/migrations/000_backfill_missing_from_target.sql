-- 000_backfill_missing_from_target.sql  (revised per 9b.1 review)
-- Adds columns that exist in OLD_DB (real data) but are missing from NEW_DB, so
-- migration cannot silently drop data. Idempotent; no DROPs; no data.
--
-- Removed vs. first draft:
--   * 9 realworld_*/upskilling_plans CREATE TABLEs (0 rows in OLD - no data at risk)
--   * students.skills / projects / certifications - OLD's denormalized arrays,
--     superseded by the normalized skills/projects/certifications tables.
--     Verified: array content is TalentForge-import preference metadata (not real
--     projects/certs); real skills exist normalized (only 'dsa','nlp' for TF232
--     have no normalized equivalent).
--   * students.branch / college_name - held pending decision (see report):
--     OLD's data in them is TF-import junk, but live code WRITES both via
--     PATCH /profile (direct_map) and the postgres shim hard-errors on unknown
--     columns, so the app needs them regardless of migration.
-- Backfilled columns are added NULLABLE so NEW's existing rows are not violated.

ALTER TABLE "applications" ADD COLUMN IF NOT EXISTS "created_at" timestamptz DEFAULT now();

ALTER TABLE "jobs" ADD COLUMN IF NOT EXISTS "batch_year" integer;
ALTER TABLE "jobs" ADD COLUMN IF NOT EXISTS "max_backlogs" integer DEFAULT 0;

ALTER TABLE "learning_resources" ADD COLUMN IF NOT EXISTS "difficulty" text;
ALTER TABLE "learning_resources" ADD COLUMN IF NOT EXISTS "duration_hours" integer;
ALTER TABLE "learning_resources" ADD COLUMN IF NOT EXISTS "is_free" boolean DEFAULT true;
ALTER TABLE "learning_resources" ADD COLUMN IF NOT EXISTS "link" text;
ALTER TABLE "learning_resources" ADD COLUMN IF NOT EXISTS "platform" text;

ALTER TABLE "matches" ADD COLUMN IF NOT EXISTS "matched_at" timestamptz DEFAULT now();

ALTER TABLE "recruiters" ADD COLUMN IF NOT EXISTS "created_at" timestamptz DEFAULT now();

ALTER TABLE "skills_graph" ADD COLUMN IF NOT EXISTS "category" text;
ALTER TABLE "skills_graph" ADD COLUMN IF NOT EXISTS "industry_demand_score" double precision;
ALTER TABLE "skills_graph" ADD COLUMN IF NOT EXISTS "related_skills" text[] DEFAULT '{}'::text[];

ALTER TABLE "students" ADD COLUMN IF NOT EXISTS "created_at" timestamptz DEFAULT now();
ALTER TABLE "students" ADD COLUMN IF NOT EXISTS "portfolio_url" text;

-- Columns required by live code (PATCH /profile writes them; shim errors on
-- unknown columns). APPROVED as columns only — their OLD values are TF-import
-- junk and are deliberately NOT migrated (see 9e mapping).
ALTER TABLE "students" ADD COLUMN IF NOT EXISTS "branch" text;
ALTER TABLE "students" ADD COLUMN IF NOT EXISTS "college_name" text;
