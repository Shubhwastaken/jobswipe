-- 002_add_student_source.sql
-- Provenance marker for the OLD->NEW data migration (Stage 9e):
--   'roster'   = row existed in NEW_DB before the merge
--   'migrated' = row inserted from OLD_DB by scripts/migrate_old_to_new.py
-- Idempotent; no DROPs; no data.

ALTER TABLE public.students ADD COLUMN IF NOT EXISTS source text;
