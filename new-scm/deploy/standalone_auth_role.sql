-- PREPARATION ONLY. DBA approval required. Connect explicitly to new_scm_dev.
-- Run in an interactive psql terminal; no password literal or generated password.
\set ON_ERROR_STOP on
SELECT current_database() = 'new_scm_dev' AS scm_target_ok \gset
\if :scm_target_ok
CREATE ROLE new_scm_auth NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE new_scm_dev TO new_scm_auth;
\password new_scm_auth
ALTER ROLE new_scm_auth LOGIN;
-- Revision 0014 grants only the explicit table/column permissions it needs.
\else
\echo FAIL database_target_rejected
\quit 1
\endif
