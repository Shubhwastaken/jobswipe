-- 003_add_skills_verified_by.sql
-- Provenance for the skills.verified flag. `verified` alone is indistinguishable
-- between a genuinely test-passed skill and one asserted by a seed/import script.
-- verified_by records HOW a skill came to be verified:
--   'skill_test' = the student passed a skill test  (the only trustworthy source)
--   'seed'       = synthetic canonical dataset (S0 students)
--   'import'     = bulk spreadsheet/roster import (TF students)
--   NULL         = unknown / not asserted
-- Additive, nullable, idempotent. `verified` itself is NOT touched, so the model
-- feature num_verified_skills is unchanged (Gate A must stay 14,400/14,400).

ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS verified_by text;

-- Backfill provenance descriptively. Only fills rows where verified_by is still
-- NULL, so re-running is safe.
UPDATE public.skills SET verified_by = 'seed'
  WHERE verified_by IS NULL AND student_id LIKE 'S0%';

UPDATE public.skills SET verified_by = 'import'
  WHERE verified_by IS NULL AND student_id LIKE 'TF%';
