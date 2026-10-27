-- Run manually with psql against 127.0.0.1:5432/new_scm_dev only.
-- This file does not set or contain a password. Do not run it automatically.
-- psql must use ON_ERROR_STOP=1 so the target check stops the script.
BEGIN;

DO $$
BEGIN
    IF current_database() <> 'new_scm_dev'
       OR inet_server_addr() IS DISTINCT FROM inet '127.0.0.1'
       OR inet_server_port() IS DISTINCT FROM 5432 THEN
        RAISE EXCEPTION 'Expected 127.0.0.1:5432/new_scm_dev';
    END IF;
END
$$;

CREATE ROLE new_scm_reader WITH
    LOGIN PASSWORD NULL
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    NOINHERIT CONNECTION LIMIT 2;

GRANT CONNECT ON DATABASE new_scm_dev TO new_scm_reader;
GRANT USAGE ON SCHEMA public TO new_scm_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO new_scm_reader;

COMMIT;
