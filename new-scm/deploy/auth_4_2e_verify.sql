-- Read-only checks. Run with psql -v ON_ERROR_STOP=1 against new_scm_dev only.
\set ON_ERROR_STOP on
SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('transaction_read_only') AS transaction_read_only;
SELECT version_num FROM public.alembic_version;
SELECT count(*) AS public_table_count FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
SELECT (SELECT count(*) FROM public.users) AS users_count,
       (SELECT count(*) FROM public.login_logs) AS login_logs_count;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN
('users', 'login_logs', 'scm_identity_mappings', 'scm_user_grants')
ORDER BY table_name;
SELECT c.relname AS table_name, con.conname, con.contype,
       pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('scm_identity_mappings', 'scm_user_grants')
ORDER BY c.relname, con.conname;
SELECT has_table_privilege('new_scm_ro', 'public.scm_identity_mappings', 'SELECT') AS mapping_select,
       has_table_privilege('new_scm_ro', 'public.scm_user_grants', 'SELECT') AS grant_select,
       has_table_privilege('new_scm_ro', 'public.scm_identity_mappings', 'INSERT') AS mapping_insert,
       has_table_privilege('new_scm_ro', 'public.scm_user_grants', 'INSERT') AS grant_insert
WHERE to_regclass('public.scm_identity_mappings') IS NOT NULL
  AND to_regclass('public.scm_user_grants') IS NOT NULL;

