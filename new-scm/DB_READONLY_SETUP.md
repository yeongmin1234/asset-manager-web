# `new_scm_dev` 로컬 읽기 계정 준비

현재 `SCM_DATABASE_URL`은 비어 있습니다. 아래 작업은 PostgreSQL 관리자 인증정보와 사용자 승인을 받은 뒤에만 수동으로 진행합니다. 기존 자산관리 DB와 NAS는 대상이 아닙니다.

## 실행 대상과 권한

- 대상: 로컬 PostgreSQL `127.0.0.1:5432`의 **`new_scm_dev`** DB, `public` 스키마.
- 실행 파일: [`deploy/create_readonly_role.sql`](deploy/create_readonly_role.sql). DB 접속 주소를 먼저 확인하고, `psql`의 `ON_ERROR_STOP=1`로 실행합니다. 파일 내부에서도 대상 주소와 DB명을 검사합니다.
- 관리자 계정은 역할 생성 권한(`CREATEROLE` 또는 superuser), `new_scm_dev`에 대한 `CONNECT` 권한을 부여할 권한, `public` 스키마에 `USAGE`를 부여할 권한, 대상 테이블들에 `SELECT`를 부여할 권한이 필요합니다. 보통 DB/스키마/테이블 소유자 또는 superuser가 해당 GRANT를 수행합니다. 소유자가 나뉘어 있다면 각 객체의 부여 권한을 확인해야 합니다.
- SQL은 `new_scm_reader`를 비밀번호 없이 만들고 `new_scm_dev.public`의 현재 테이블에 `SELECT`만 부여합니다. 쓰기 권한과 향후 생성될 테이블의 권한은 부여하지 않습니다. 역할이 이미 있으면 오류로 중단합니다.

승인 후, 관리자가 저장소 루트의 대화형 PowerShell 터미널에서 다음 명령을 실행합니다. 이 컴퓨터에서는 `psql`이 PATH에 없고 PostgreSQL 17 설치 경로에 있습니다. `ADMIN_ROLE`은 별도로 준비한 PostgreSQL 관리자 계정명으로 바꾸며, 비밀번호는 명령행이나 파일에 넣지 않습니다.

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -p 5432 -U ADMIN_ROLE -d new_scm_dev -v ON_ERROR_STOP=1 -f .\new-scm\deploy\create_readonly_role.sql
```

그다음 같은 관리자 계정으로 `psql`에 다시 대화형 접속하여 프롬프트에서 `\password new_scm_reader`를 실행합니다. `\password`는 `psql` 명령이며 SQL 파일에 저장하지 않습니다. 비밀번호를 팀 채팅, 명령행 인수, Git에 남기지 않습니다.

PostgreSQL의 `PUBLIC` 또는 기존 역할 멤버십을 통해 다른 DB의 `CONNECT`, 테이블 쓰기 권한, DB/스키마 생성 권한이 상속될 수 있습니다. 새 역할에 부여한 권한만으로 전체 서버에서의 접근 제한을 보장할 수 없으므로, 아래 실제 권한 검증이 통과하기 전에는 읽기 전용이라고 판정하지 않습니다. 다른 DB의 `PUBLIC` 권한이나 서버 인증 설정은 여기서 변경하지 않습니다.

## 계정 준비 후 검증

1. `new_scm_reader`로 `127.0.0.1:5432/new_scm_dev`에 대화형 접속하고 `SELECT current_database(), current_user, current_setting('transaction_read_only');`를 실행합니다. 접속 시 `default_transaction_read_only=on`을 지정합니다.
2. 다음 쿼리로 API와 동일한 `public` 기본 테이블 수를 확인하고, 기대값 51과 비교합니다.

   ```sql
   SELECT count(*) FROM information_schema.tables
   WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
   ```

3. `SELECT version_num FROM public.alembic_version;`로 실제 Alembic 버전을 확인합니다.
4. 다음 쿼리의 `insertable`, `updatable`, `deletable`이 모두 0인지 확인합니다. 대상 DB의 모든 사용자 스키마에 있는 테이블, 뷰, 외부 테이블의 테이블/열 단위 실효 권한을 검사하므로 `PUBLIC` 등에서 얻은 권한도 드러납니다.

   ```sql
   SELECT count(*) AS relations_checked,
          count(*) FILTER (WHERE has_table_privilege(current_user, c.oid, 'INSERT')
                           OR has_any_column_privilege(current_user, c.oid, 'INSERT')) AS insertable,
          count(*) FILTER (WHERE has_table_privilege(current_user, c.oid, 'UPDATE')
                           OR has_any_column_privilege(current_user, c.oid, 'UPDATE')) AS updatable,
          count(*) FILTER (WHERE has_table_privilege(current_user, c.oid, 'DELETE')) AS deletable
   FROM pg_catalog.pg_class AS c
   JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
   WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
     AND n.nspname NOT LIKE 'pg_toast%'
     AND n.nspname NOT LIKE 'pg_temp_%'
     AND c.relkind IN ('r', 'p', 'v', 'f');
   ```

5. DB/스키마 생성 권한도 확인합니다: `SELECT has_database_privilege(current_user, current_database(), 'CREATE'), has_schema_privilege(current_user, 'public', 'CREATE');`. `PUBLIC` 권한으로 허용될 수 있습니다. 사용자 시퀀스의 `UPDATE` 권한도 다음 쿼리의 결과가 0인지 확인합니다.

   ```sql
   SELECT count(*) FILTER (WHERE has_sequence_privilege(current_user, c.oid, 'UPDATE')) AS updatable_sequences
   FROM pg_catalog.pg_class AS c
   JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
   WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
     AND n.nspname NOT LIKE 'pg_toast%'
     AND n.nspname NOT LIKE 'pg_temp_%'
     AND c.relkind = 'S';
   ```
6. 비밀번호를 URL 인코딩하여 **`new-scm/.env`에만** `SCM_DATABASE_URL=postgresql+psycopg://new_scm_reader:...@127.0.0.1:5432/new_scm_dev` 형식으로 설정합니다. 실제 비밀번호나 전체 URL은 출력하거나 Git에 저장하지 않습니다. `.env`는 `new-scm/.gitignore`에서 제외됩니다.
7. 신규 SCM 백엔드를 127.0.0.1:8012에서 실행하고, 기존 `SCM_DIAGNOSTICS_KEY`로 `/api/v1/system/db-status`를 호출하여 `connected=true`, `read_only=true`, `table_count=51`을 확인합니다. 응답과 보고서에 인증정보를 포함하지 않습니다.

`SELECT` 확인과 권한 조회는 읽기 전용으로 수행합니다. `INSERT`, `UPDATE`, `DELETE` 문은 실행하지 않습니다.
