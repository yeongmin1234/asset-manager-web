# PostgreSQL 16 권한·소유권 이전 계획 (실행 전 검토용)

이 문서는 SQL 계획이다. 어떤 단계도 자동 실행하지 않는다. 모든 SQL은 `asset_manager_prod`에 연결한 관리 세션에서 **단계별로 수동 실행**한다. 실행 전 백업과 현재 ACL·소유자 조회 결과를 보관하고, 각 단계의 검증 결과를 확인한 뒤 다음 단계로 간다. `asset_user`가 아직 SUPERUSER이면 `has_*_privilege` 결과가 ACL과 무관하게 참일 수 있으므로, 아래 검증은 직접 부여된 ACL 항목을 확인한다.

범위: `public`의 업무 테이블 41개, 시퀀스 39개, ENUM 7개와 별도 테이블 `public.alembic_version` 1개. 이 수가 실제 DB와 다르면 **중단하고 대상 목록부터 다시 확인**한다. 41개는 `alembic_version`을 제외한 수로 가정한다. 현재 소유자는 모두 `asset_user`, 현재 DB 소유자도 `asset_user`라는 전제다. 다른 소유자가 발견되면 중단한다. `public` 외 스키마와 뷰·함수 등은 이 계획의 대상이 아니다.

실행 전 다음 결과를 저장한다. 특히 ACL 및 default ACL 결과는 Rollback에서 변경 전 권한을 복원하는 기준이다.

```sql
SELECT current_database(), current_user, current_setting('server_version');
SELECT datname, pg_get_userbyid(datdba) AS owner, datacl
FROM pg_database WHERE datname = 'asset_manager_prod';
SELECT nspname, pg_get_userbyid(nspowner) AS owner, nspacl
FROM pg_namespace WHERE nspname = 'public';
SELECT c.oid::regclass AS object_name, c.relkind, pg_get_userbyid(c.relowner) AS owner, c.relacl
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S')
ORDER BY c.relkind, c.relname;
SELECT t.oid::regtype AS type_name, pg_get_userbyid(t.typowner) AS owner, t.typacl
FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' AND t.typtype = 'e'
ORDER BY t.typname;
SELECT pg_get_userbyid(d.defaclrole) AS creator, d.defaclnamespace::regnamespace AS schema_name,
       d.defaclobjtype, d.defaclacl
FROM pg_default_acl d
WHERE d.defaclrole IN ('asset_user'::regrole, 'asset_migrator'::regrole)
ORDER BY 1, 2, 3;
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname = 'asset_user';
```

## [1단계 - 트랜잭션 SQL]

`ON_ERROR_STOP`을 켠 psql 등 오류 시 멈추는 클라이언트로 실행한다. `DO`에서 예외가 나면 `COMMIT`하지 말고 `ROLLBACK`한다. 실행 주체는 객체 소유권 변경과 `FOR ROLE asset_migrator` default privileges 변경 권한이 있어야 한다. 아래의 사전 개수·소유자 검증은 변경 전에 실행된다.

```sql
BEGIN;

DO $check$
DECLARE
    business_tables integer;
    sequences integer;
    enums integer;
    version_tables integer;
    wrong_owner integer;
BEGIN
    IF current_database() <> 'asset_manager_prod' THEN
        RAISE EXCEPTION 'Wrong database: %', current_database();
    END IF;
    IF current_setting('server_version_num')::integer / 10000 <> 16 THEN
        RAISE EXCEPTION 'PostgreSQL 16 required';
    END IF;
    IF (SELECT pg_get_userbyid(datdba) FROM pg_database
        WHERE datname = current_database()) <> 'asset_user' THEN
        RAISE EXCEPTION 'Unexpected database owner';
    END IF;

    SELECT count(*) FILTER (WHERE c.relkind IN ('r', 'p') AND c.relname <> 'alembic_version'),
           count(*) FILTER (WHERE c.relkind = 'S'),
           count(*) FILTER (WHERE c.relkind IN ('r', 'p') AND c.relname = 'alembic_version'),
           count(*) FILTER (WHERE pg_get_userbyid(c.relowner) <> 'asset_user')
      INTO business_tables, sequences, version_tables, wrong_owner
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S');

    SELECT count(*) INTO enums
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'public' AND t.typtype = 'e';
    SELECT wrong_owner + count(*) INTO wrong_owner
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'public' AND t.typtype = 'e'
      AND pg_get_userbyid(t.typowner) <> 'asset_user';

    IF business_tables <> 41 OR sequences <> 39 OR enums <> 7
       OR version_tables <> 1 OR wrong_owner <> 0 THEN
        RAISE EXCEPTION 'Unexpected objects/owners: tables %, sequences %, enums %, alembic %, wrong owners %',
            business_tables, sequences, enums, version_tables, wrong_owner;
    END IF;
END
$check$;

-- 앱 권한을 소유권 이전 전에 명시한다. alembic_version은 제외한다.
GRANT CONNECT ON DATABASE asset_manager_prod TO asset_user;
GRANT USAGE ON SCHEMA public TO asset_user;
DO $grant_app$
DECLARE obj record;
BEGIN
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname <> 'alembic_version'
        ORDER BY c.relname
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S' ORDER BY c.relname
    LOOP
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE public.%I TO asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype = 'e' ORDER BY t.typname
    LOOP
        EXECUTE format('GRANT USAGE ON TYPE public.%I TO asset_user', obj.typname);
    END LOOP;
END
$grant_app$;

GRANT CONNECT ON DATABASE asset_manager_prod TO asset_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO asset_migrator;

DO $transfer$
DECLARE obj record;
BEGIN
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
        ORDER BY c.relname
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO asset_migrator', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
          AND c.relowner <> 'asset_migrator'::regrole
        ORDER BY c.relname
    LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO asset_migrator', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype = 'e'
        ORDER BY t.typname
    LOOP
        EXECUTE format('ALTER TYPE public.%I OWNER TO asset_migrator', obj.typname);
    END LOOP;
END
$transfer$;

-- 소유권 변경은 옛 소유자의 ACL에 영향을 줄 수 있으므로 앱 권한을 다시 확정한다.
DO $grant_after_owner$
DECLARE obj record;
BEGIN
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname <> 'alembic_version'
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
    LOOP
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE public.%I TO asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype = 'e'
    LOOP
        EXECUTE format('GRANT USAGE ON TYPE public.%I TO asset_user', obj.typname);
    END LOOP;
END
$grant_after_owner$;

-- asset_migrator가 앞으로 public에 만드는 객체에만 적용된다.
ALTER DEFAULT PRIVILEGES FOR ROLE asset_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO asset_user;
ALTER DEFAULT PRIVILEGES FOR ROLE asset_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO asset_user;
ALTER DEFAULT PRIVILEGES FOR ROLE asset_migrator IN SCHEMA public
    GRANT USAGE ON TYPES TO asset_user;

DO $verify$
DECLARE
    table_count integer;
    seq_count integer;
    enum_count integer;
    all_tables integer;
    all_sequences integer;
    all_enums integer;
    missing integer;
BEGIN
    SELECT count(*) FILTER (WHERE c.relkind IN ('r', 'p') AND c.relname <> 'alembic_version'
                            AND c.relowner = 'asset_migrator'::regrole),
           count(*) FILTER (WHERE c.relkind = 'S' AND c.relowner = 'asset_migrator'::regrole),
           count(*) FILTER (WHERE c.relkind IN ('r', 'p') AND c.relname <> 'alembic_version'),
           count(*) FILTER (WHERE c.relkind = 'S')
      INTO table_count, seq_count, all_tables, all_sequences
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S');
    SELECT count(*) FILTER (WHERE t.typowner = 'asset_migrator'::regrole), count(*)
      INTO enum_count, all_enums
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'public' AND t.typtype = 'e';
    IF table_count <> 41 OR seq_count <> 39 OR enum_count <> 7
       OR all_tables <> 41 OR all_sequences <> 39 OR all_enums <> 7
       OR (SELECT c.relowner FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'public' AND c.relname = 'alembic_version'
             AND c.relkind IN ('r', 'p')) IS DISTINCT FROM 'asset_migrator'::regrole THEN
        RAISE EXCEPTION 'Owner verification failed';
    END IF;

    SELECT count(*) INTO missing FROM (
        SELECT c.oid, required.privilege
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE')) required(privilege)
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname <> 'alembic_version'
          AND NOT EXISTS (
              SELECT 1 FROM aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
              WHERE a.grantee = 'asset_user'::regrole AND a.privilege_type = required.privilege)
        UNION ALL
        SELECT c.oid, required.privilege
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        CROSS JOIN (VALUES ('USAGE'), ('SELECT')) required(privilege)
        WHERE n.nspname = 'public' AND c.relkind = 'S'
          AND NOT EXISTS (
              SELECT 1 FROM aclexplode(coalesce(c.relacl, acldefault('s', c.relowner))) a
              WHERE a.grantee = 'asset_user'::regrole AND a.privilege_type = required.privilege)
        UNION ALL
        SELECT t.oid, 'USAGE'
        FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype = 'e'
          AND NOT EXISTS (
              SELECT 1 FROM aclexplode(coalesce(t.typacl, acldefault('T', t.typowner))) a
              WHERE a.grantee = 'asset_user'::regrole AND a.privilege_type = 'USAGE')
    ) gaps;
    IF missing <> 0 THEN RAISE EXCEPTION 'Missing explicit app ACL entries: %', missing; END IF;

    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
             LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
        WHERE n.nspname = 'public' AND c.relname = 'alembic_version'
          AND c.relkind IN ('r', 'p') AND a.grantee = 'asset_user'::regrole
          AND a.privilege_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE')) THEN
        RAISE EXCEPTION 'asset_user has direct DML on alembic_version';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace n,
             LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
        WHERE n.nspname = 'public' AND a.grantee = 'asset_migrator'::regrole
          AND a.privilege_type = 'CREATE') THEN
        RAISE EXCEPTION 'Missing explicit asset_migrator schema CREATE';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace n,
             LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
        WHERE n.nspname = 'public' AND a.grantee = 'asset_migrator'::regrole
          AND a.privilege_type = 'USAGE') THEN
        RAISE EXCEPTION 'Missing explicit asset_migrator schema USAGE';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_database d,
             LATERAL aclexplode(coalesce(d.datacl, acldefault('d', d.datdba))) a
        WHERE d.datname = 'asset_manager_prod'
          AND a.grantee = 'asset_migrator'::regrole AND a.privilege_type = 'CONNECT') THEN
        RAISE EXCEPTION 'Missing explicit asset_migrator CONNECT';
    END IF;

    SELECT count(*) INTO missing FROM (
        SELECT req.objtype, req.privilege
        FROM (VALUES ('r'::"char", 'SELECT'), ('r'::"char", 'INSERT'),
                     ('r'::"char", 'UPDATE'), ('r'::"char", 'DELETE'),
                     ('S'::"char", 'USAGE'), ('S'::"char", 'SELECT'),
                     ('T'::"char", 'USAGE')) req(objtype, privilege)
        WHERE NOT EXISTS (
            SELECT 1 FROM pg_default_acl d
            JOIN pg_namespace n ON n.oid = d.defaclnamespace,
                 LATERAL aclexplode(d.defaclacl) a
            WHERE d.defaclrole = 'asset_migrator'::regrole
              AND n.nspname = 'public' AND d.defaclobjtype = req.objtype
              AND a.grantee = 'asset_user'::regrole AND a.privilege_type = req.privilege)
    ) gaps;
    IF missing <> 0 THEN RAISE EXCEPTION 'Missing default privilege entries: %', missing; END IF;
END
$verify$;

COMMIT;
```

## [1단계 검증 SQL]

아래는 `COMMIT` 후 별도 읽기 전용 세션에서 확인한다. 개수는 각각 `41 / 39 / 7 / 1`이어야 하고, `unexpected_alembic_dml`은 0행이어야 한다. 기존 `alembic_version` 직접 DML이 남아 있으면 1단계 트랜잭션 검증에서 중단된다.

```sql
SELECT count(*) FILTER (WHERE c.relkind IN ('r','p') AND c.relname <> 'alembic_version'
                        AND c.relowner = 'asset_migrator'::regrole) AS owned_business_tables,
       count(*) FILTER (WHERE c.relkind = 'S' AND c.relowner = 'asset_migrator'::regrole) AS owned_sequences,
       count(*) FILTER (WHERE c.relname = 'alembic_version' AND c.relkind IN ('r','p')
                        AND c.relowner = 'asset_migrator'::regrole) AS owned_alembic_version
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r','p','S');
SELECT count(*) AS owned_enums
FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' AND t.typtype = 'e'
  AND t.typowner = 'asset_migrator'::regrole;

-- 164개 업무 테이블 ACL, 78개 시퀀스 ACL, 7개 ENUM ACL 항목이 보여야 한다.
SELECT 'table' AS object_kind, count(DISTINCT (c.oid, a.privilege_type)) AS explicit_app_privileges
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
WHERE n.nspname = 'public' AND c.relkind IN ('r','p') AND c.relname <> 'alembic_version'
  AND a.grantee = 'asset_user'::regrole
  AND a.privilege_type IN ('SELECT','INSERT','UPDATE','DELETE')
UNION ALL
SELECT 'sequence', count(DISTINCT (c.oid, a.privilege_type))
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL aclexplode(coalesce(c.relacl, acldefault('s', c.relowner))) a
WHERE n.nspname = 'public' AND c.relkind = 'S'
  AND a.grantee = 'asset_user'::regrole AND a.privilege_type IN ('USAGE','SELECT')
UNION ALL
SELECT 'enum', count(DISTINCT (t.oid, a.privilege_type))
FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace,
     LATERAL aclexplode(coalesce(t.typacl, acldefault('T', t.typowner))) a
WHERE n.nspname = 'public' AND t.typtype = 'e'
  AND a.grantee = 'asset_user'::regrole AND a.privilege_type = 'USAGE';

SELECT c.relname, a.privilege_type AS unexpected_alembic_dml
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
WHERE n.nspname = 'public' AND c.relname = 'alembic_version'
  AND a.grantee = 'asset_user'::regrole
  AND a.privilege_type IN ('SELECT','INSERT','UPDATE','DELETE');

SELECT a.grantee::regrole AS grantee, a.privilege_type
FROM pg_namespace n,
     LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
WHERE n.nspname = 'public' AND a.grantee = 'asset_migrator'::regrole
  AND a.privilege_type IN ('USAGE','CREATE');

SELECT d.datname, a.grantee::regrole AS grantee, a.privilege_type
FROM pg_database d,
     LATERAL aclexplode(coalesce(d.datacl, acldefault('d', d.datdba))) a
WHERE d.datname = 'asset_manager_prod'
  AND a.grantee = 'asset_migrator'::regrole AND a.privilege_type = 'CONNECT';

SELECT d.defaclobjtype, a.privilege_type, a.grantee::regrole AS grantee
FROM pg_default_acl d JOIN pg_namespace n ON n.oid = d.defaclnamespace,
     LATERAL aclexplode(d.defaclacl) a
WHERE d.defaclrole = 'asset_migrator'::regrole AND n.nspname = 'public'
  AND a.grantee = 'asset_user'::regrole
ORDER BY d.defaclobjtype, a.privilege_type;
```

## [2단계 - DB owner 변경]

1단계 `COMMIT` 및 검증 완료 후 **별도 명령**으로 실행한다. 이 문서에서 `BEGIN`과 `COMMIT`으로 감싸지 않는다.

```sql
ALTER DATABASE asset_manager_prod OWNER TO asset_db_admin;
```

## [2단계 검증 SQL]

```sql
SELECT datname, pg_get_userbyid(datdba) AS owner
FROM pg_database WHERE datname = 'asset_manager_prod';
-- owner = asset_db_admin
```

## [3단계 - 권한 정리]

먼저 다음 **조회만** 실행하고 결과를 보관한다. `PUBLIC`은 역할 이름이 아닌 모든 역할을 뜻한다. `asset_user`가 가진 CREATE가 직접 부여, `PUBLIC`, 역할 상속, 스키마 소유권 중 어느 경로인지 확인한다.

```sql
SELECT n.nspname, pg_get_userbyid(n.nspowner) AS schema_owner, n.nspacl,
       a.grantee, CASE WHEN a.grantee = 0 THEN 'PUBLIC'
                       ELSE pg_get_userbyid(a.grantee) END AS grantee_name,
       a.privilege_type, a.is_grantable
FROM pg_namespace n,
     LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
WHERE n.nspname = 'public'
ORDER BY grantee_name, a.privilege_type;
SELECT has_schema_privilege('asset_user', 'public', 'CREATE') AS effective_app_create,
       has_schema_privilege('asset_migrator', 'public', 'CREATE') AS effective_migrator_create;
SELECT member.rolname AS member, parent.rolname AS granted_role,
       auth.inherit_option, auth.set_option
FROM pg_auth_members auth
JOIN pg_roles member ON member.oid = auth.member
JOIN pg_roles parent ON parent.oid = auth.roleid
WHERE member.rolname IN ('asset_user', 'asset_migrator');
```

ACL 확인 후 `asset_user`의 직접 CREATE와 불필요한 객체 권한을 정리한다. 실행 전 1단계와 같은 객체 개수가 유지되는지 다시 확인한다. 다른 앱이 `PUBLIC` CREATE에 의존하는지 확인되기 전에는 그 권한을 변경하지 않는다. `asset_user`가 SUPERUSER인 동안 effective 권한 검사는 정리 결과를 증명하지 못한다.

```sql
DO $check_scope$
BEGIN
    IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
          AND c.relname <> 'alembic_version') <> 41
       OR (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'public' AND c.relkind = 'S') <> 39
       OR (SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
           WHERE n.nspname = 'public' AND t.typtype = 'e') <> 7 THEN
        RAISE EXCEPTION 'Object counts changed; stop cleanup';
    END IF;
END
$check_scope$;

REVOKE CREATE ON SCHEMA public FROM asset_user;

DO $cleanup$
DECLARE obj record;
BEGIN
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
    LOOP
        EXECUTE format('REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE public.%I FROM asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
    LOOP
        EXECUTE format('REVOKE UPDATE ON SEQUENCE public.%I FROM asset_user', obj.relname);
    END LOOP;
END
$cleanup$;
```

`PUBLIC` CREATE 철회는 **위 ACL 조회에서 `PUBLIC`의 직접 CREATE 항목이 확인되고, 의존성 검토와 별도 선택이 끝난 경우에만** 주석을 해제해 수동 실행한다. 기본 실행 SQL에는 포함하지 않는다.

```sql
-- 선택 단계: ACL 및 다른 사용자 영향 확인 후에만 별도로 실행
-- REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

`public` 스키마 자체의 소유자가 `asset_user`이거나 `asset_user`가 상속한 역할이 CREATE를 제공하면, 직접 CREATE 철회만으로 권한을 제한할 수 없다. 스키마 소유권 변경은 이 계획의 범위 밖이므로 ACL·역할 구조를 따로 검토한다.

## [3단계 검증 SQL]

다음 조회의 `asset_user` 직접 CREATE, 불필요한 테이블·시퀀스 ACL은 **0행**이어야 한다. `PUBLIC` CREATE 조회는 선택 단계의 실행 여부와 대조한다. 1단계 검증 SQL도 다시 실행해 필요한 앱 권한과 migrator CREATE가 유지되는지 확인한다.

```sql
SELECT a.grantee, CASE WHEN a.grantee = 0 THEN 'PUBLIC'
                       ELSE pg_get_userbyid(a.grantee) END AS grantee_name,
       a.privilege_type
FROM pg_namespace n,
     LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
WHERE n.nspname = 'public' AND a.privilege_type = 'CREATE'
  AND a.grantee IN (0, 'asset_user'::regrole, 'asset_migrator'::regrole);

SELECT c.oid::regclass AS table_name, a.privilege_type
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
  AND a.grantee = 'asset_user'::regrole
  AND a.privilege_type IN ('TRUNCATE','REFERENCES','TRIGGER');

SELECT c.oid::regclass AS sequence_name, a.privilege_type
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL aclexplode(coalesce(c.relacl, acldefault('s', c.relowner))) a
WHERE n.nspname = 'public' AND c.relkind = 'S'
  AND a.grantee = 'asset_user'::regrole AND a.privilege_type = 'UPDATE';
```

## [Rollback]

역순으로 되돌린다. 각 단계는 독립 실행·검증한다. 변경 전 ACL 스냅샷과 비교해 **이번 계획에서 새로 더한 권한만** 철회한다. 이전부터 있던 권한을 무조건 철회하면 원상 복구가 아니다. 1단계 트랜잭션이 실패해 `ROLLBACK`되었다면 2·3단계는 실행하지 않았으므로 추가 복구가 없다.

### 3단계 되돌리기 — ACL 스냅샷 기준 별도 명령

아래 GRANT는 3단계 전에 해당 ACL 항목이 있었던 객체에만 적용한다. `PUBLIC` CREATE를 선택적으로 철회했다면, 변경 전 스냅샷에 `PUBLIC` CREATE가 있었을 때에만 복원한다.

```sql
-- 조건부 예시: 변경 전 ACL에 있던 항목만 객체별로 복원
-- GRANT CREATE ON SCHEMA public TO asset_user;
-- GRANT TRUNCATE, REFERENCES, TRIGGER ON TABLE public.<원래_권한이_있던_테이블> TO asset_user;
-- GRANT UPDATE ON SEQUENCE public.<원래_권한이_있던_시퀀스> TO asset_user;
-- GRANT CREATE ON SCHEMA public TO PUBLIC;  -- 선택 철회가 실행된 경우에만
```

복원 후 `3단계 검증 SQL`을 재실행해 저장한 변경 전 ACL과 대조한다.

### 2단계 되돌리기 — 별도 명령

변경 전 DB 소유자가 `asset_user`였음을 다시 확인한 뒤 실행한다.

```sql
ALTER DATABASE asset_manager_prod OWNER TO asset_user;
SELECT datname, pg_get_userbyid(datdba) AS owner
FROM pg_database WHERE datname = 'asset_manager_prod';
-- owner = asset_user
```

### 1단계 되돌리기 — 별도 트랜잭션

객체 수·소유자와 현재 ACL을 먼저 확인한다. 아래 소유권 복구는 1단계에서 이전한 객체만 대상으로 한다. 마지막 권한 철회 구문은 **스냅샷상 원래 없던 권한에 한해서만** 실행한다. `alembic_version`에 DML을 부여하는 구문은 없다.

```sql
BEGIN;

DO $check_rollback_scope$
BEGIN
    IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
          AND c.relname <> 'alembic_version' AND c.relowner = 'asset_migrator'::regrole) <> 41
       OR (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'public' AND c.relkind = 'S'
             AND c.relowner = 'asset_migrator'::regrole) <> 39
       OR (SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
           WHERE n.nspname = 'public' AND t.typtype = 'e'
             AND t.typowner = 'asset_migrator'::regrole) <> 7
       OR (SELECT c.relowner FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'public' AND c.relname = 'alembic_version'
             AND c.relkind IN ('r','p')) IS DISTINCT FROM 'asset_migrator'::regrole THEN
        RAISE EXCEPTION 'Owner/count drift; stop rollback';
    END IF;
END
$check_rollback_scope$;

DO $restore_owner$
DECLARE obj record;
BEGIN
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
          AND c.relowner = 'asset_migrator'::regrole
        ORDER BY c.relname
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
          AND c.relowner = 'asset_migrator'::regrole
    LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO asset_user', obj.relname);
    END LOOP;
    FOR obj IN
        SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype = 'e'
          AND t.typowner = 'asset_migrator'::regrole
    LOOP
        EXECUTE format('ALTER TYPE public.%I OWNER TO asset_user', obj.typname);
    END LOOP;
END
$restore_owner$;

-- 아래 default ACL 항목은 1단계 전에 없었던 privilege만 골라 철회
-- ALTER DEFAULT PRIVILEGES FOR ROLE asset_migrator IN SCHEMA public
--     REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM asset_user;
-- ALTER DEFAULT PRIVILEGES FOR ROLE asset_migrator IN SCHEMA public
--     REVOKE USAGE, SELECT ON SEQUENCES FROM asset_user;
-- ALTER DEFAULT PRIVILEGES FOR ROLE asset_migrator IN SCHEMA public
--     REVOKE USAGE ON TYPES FROM asset_user;

-- 다음 항목은 변경 전 스냅샷에 없었던 것만 선별 철회
-- REVOKE CONNECT ON DATABASE asset_manager_prod FROM asset_migrator;
-- REVOKE USAGE, CREATE ON SCHEMA public FROM asset_migrator;
-- REVOKE CONNECT ON DATABASE asset_manager_prod FROM asset_user;
-- REVOKE USAGE ON SCHEMA public FROM asset_user;
-- REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE public.<이번에_추가한_권한의_테이블> FROM asset_user;
-- REVOKE USAGE, SELECT ON SEQUENCE public.<이번에_추가한_권한의_시퀀스> FROM asset_user;
-- REVOKE USAGE ON TYPE public.<이번에_추가한_권한의_ENUM> FROM asset_user;

-- 저장한 변경 전 owner/ACL과 비교 후에만 COMMIT
COMMIT;
```

Rollback 1단계 검증: `1단계 검증 SQL`의 소유자 조회를 `asset_user` 기준으로 다시 실행해 `41 / 39 / 7 / 1`을 확인하고, 실행 전 저장한 객체별 ACL 및 default ACL과 비교한다. 새로운 migration으로 객체가 늘었다면 그 객체를 임의로 `asset_user`에 이전하지 말고 범위를 다시 정한다.

## [아직 하지 않을 작업]

- `asset_user`의 `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION`, `BYPASSRLS` 속성 제거 또는 변경.
- 사전 ACL 확인과 영향 검토 전 `REVOKE CREATE ON SCHEMA public FROM PUBLIC` 실행.
- 이 SQL 계획의 자동 실행, 운영 DB 접속, 1~3단계의 일괄 실행.
- `alembic_version`에 `asset_user` DML 권한 부여. Default privileges는 앞으로 생성되는 **모든** 테이블에 적용되므로 이 테이블을 나중에 재생성하면 별도 ACL 확인과 철회가 필요하다.

PostgreSQL 16 근거: [권한과 소유권](https://www.postgresql.org/docs/16/ddl-priv.html), [GRANT](https://www.postgresql.org/docs/16/sql-grant.html), [REVOKE](https://www.postgresql.org/docs/16/sql-revoke.html), [ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html), [ALTER DATABASE](https://www.postgresql.org/docs/16/sql-alterdatabase.html).
