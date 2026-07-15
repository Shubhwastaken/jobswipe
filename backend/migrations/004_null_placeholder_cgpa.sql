-- 004_null_placeholder_cgpa.sql
-- Backfill: the placeholder/test accounts hold a literal cgpa=0, which the
-- three-state eligibility engine reads as a KNOWN failing value (ineligible)
-- rather than 'not on file' (incomplete). Set their cgpa to NULL so they behave
-- like a real new signup (which now writes NULL — see auth.py).
--
-- EXPLICIT ALLOWLIST by student_id — exactly the 10 probed placeholder accounts,
-- nothing else. A cgpa=0 predicate was rejected: it could match an S0 row keyed
-- unexpectedly (corrupting Gate A / paper parity) or a future cgpa=0 account.
-- This cannot hit an S0 row regardless of how S0 is keyed, and cannot hit any
-- account not named here. Marks are already NULL for these accounts (never
-- written on insert). Idempotent.

UPDATE public.students
   SET cgpa = NULL
 WHERE student_id IN (
    'alice',
    'arjun',
    'kavyaghosh',
    'prakarsh',
    'shubh',
    'studentname',
    'RA2311047010001',
    'RA2311047019999',
    'RA2311047098888',
    'RA2311047099999'
 );
