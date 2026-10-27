# 신규 SCM PostgreSQL 스키마 실측 카탈로그

- 조회일: 2026-10-27 (Asia/Seoul)
- 대상: `127.0.0.1:5432/new_scm_dev`, `public`; 접속 역할 `new_scm_ro`
- 세션: `transaction_read_only=on`; `SELECT`만 실행하고 연결 종료 시 롤백
- 기본 테이블: 52개 (업무 51개 + `alembic_version` 1개)
- Alembic: `20260729_0012`

아래 값은 PostgreSQL 시스템 카탈로그에서 읽은 **실제 구조**다. 제약 정의의 참조 테이블과 컬럼을 FK 근거로 사용한다. 업무 상태 전이, 인증 정책, 데이터 품질은 이 메타데이터만으로 검증되지 않는다.

## 테이블·컬럼·제약·인덱스

### `alembic_version`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `version_num` | `character varying(32)` | 불가 | — |

**제약조건**

- PK `alembic_version_pkc`: `PRIMARY KEY (version_num)`

**인덱스**

- `alembic_version_pkc`: `CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)`

### `as_notes`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('as_notes_id_seq'::regclass)` |
| `as_request_id` | `bigint` | 불가 | — |
| `author_user_id` | `bigint` | 허용 | — |
| `author_username` | `character varying(50)` | 불가 | — |
| `note_type` | `character varying(30)` | 불가 | — |
| `content` | `text` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `as_notes_as_request_id_fkey`: `FOREIGN KEY (as_request_id) REFERENCES as_requests(id) ON DELETE RESTRICT`
- FK `as_notes_author_user_id_fkey`: `FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `as_notes_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `as_notes_pkey`: `CREATE UNIQUE INDEX as_notes_pkey ON public.as_notes USING btree (id)`
- `ix_as_notes_as_request_id`: `CREATE INDEX ix_as_notes_as_request_id ON public.as_notes USING btree (as_request_id)`
- `ix_as_notes_created_at`: `CREATE INDEX ix_as_notes_created_at ON public.as_notes USING btree (created_at)`
- `ix_as_notes_note_type`: `CREATE INDEX ix_as_notes_note_type ON public.as_notes USING btree (note_type)`

### `as_part_codes`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('as_part_codes_id_seq'::regclass)` |
| `part_code` | `character varying(50)` | 불가 | — |
| `part_name` | `character varying(150)` | 불가 | — |
| `category_code` | `character varying(50)` | 허용 | — |
| `product_id` | `bigint` | 허용 | — |
| `unit` | `character varying(30)` | 허용 | — |
| `standard_cost` | `numeric(14,2)` | 허용 | — |
| `description` | `character varying(500)` | 허용 | — |
| `is_active` | `boolean` | 불가 | — |
| `sort_order` | `integer` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_as_part_cost`: `CHECK (standard_cost IS NULL OR standard_cost >= 0::numeric)`
- FK `as_part_codes_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `as_part_codes_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `as_part_codes_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `as_part_codes_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `as_part_codes_pkey`: `CREATE UNIQUE INDEX as_part_codes_pkey ON public.as_part_codes USING btree (id)`
- `ix_as_part_active`: `CREATE INDEX ix_as_part_active ON public.as_part_codes USING btree (is_active)`
- `ix_as_part_category`: `CREATE INDEX ix_as_part_category ON public.as_part_codes USING btree (category_code)`
- `ix_as_part_code`: `CREATE UNIQUE INDEX ix_as_part_code ON public.as_part_codes USING btree (part_code)`
- `ix_as_part_product`: `CREATE INDEX ix_as_part_product ON public.as_part_codes USING btree (product_id)`

### `as_requests`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('as_requests_id_seq'::regclass)` |
| `as_code` | `character varying(30)` | 불가 | — |
| `source_consultation_id` | `bigint` | 허용 | — |
| `customer_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `serial_number` | `character varying(150)` | 불가 | — |
| `assigned_employee_id` | `bigint` | 허용 | — |
| `received_store_id` | `bigint` | 허용 | — |
| `request_type` | `character varying(30)` | 불가 | — |
| `symptom` | `text` | 불가 | — |
| `diagnosis` | `text` | 허용 | — |
| `resolution` | `text` | 허용 | — |
| `status` | `character varying(30)` | 불가 | — |
| `priority` | `character varying(20)` | 불가 | — |
| `received_at` | `timestamp with time zone` | 불가 | — |
| `expected_completion_at` | `timestamp with time zone` | 허용 | — |
| `completed_at` | `timestamp with time zone` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `warranty_status` | `character varying(30)` | 불가 | — |
| `repair_cost` | `numeric(14,2)` | 허용 | — |
| `shipping_tracking_number` | `character varying(100)` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_as_requests_priority`: `CHECK (priority::text = ANY (ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'urgent'::character varying]::text[]))`
- CHECK `ck_as_requests_repair_cost_nonnegative`: `CHECK (repair_cost IS NULL OR repair_cost >= 0::numeric)`
- CHECK `ck_as_requests_status`: `CHECK (status::text = ANY (ARRAY['received'::character varying, 'inspecting'::character varying, 'waiting_parts'::character varying, 'repairing'::character varying, 'waiting_customer'::character varying, 'ready_to_ship'::character varying, 'shipped'::character varying, 'visit_scheduled'::character varying, 'completed'::character varying, 'cancelled'::character varying]::text[]))`
- CHECK `ck_as_requests_warranty_status`: `CHECK (warranty_status::text = ANY (ARRAY['unknown'::character varying, 'in_warranty'::character varying, 'out_of_warranty'::character varying]::text[]))`
- FK `as_requests_assigned_employee_id_fkey`: `FOREIGN KEY (assigned_employee_id) REFERENCES employees(id) ON DELETE SET NULL`
- FK `as_requests_customer_id_fkey`: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT`
- FK `as_requests_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `as_requests_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `as_requests_received_store_id_fkey`: `FOREIGN KEY (received_store_id) REFERENCES stores(id) ON DELETE SET NULL`
- FK `as_requests_source_consultation_id_fkey`: `FOREIGN KEY (source_consultation_id) REFERENCES consultations(id) ON DELETE RESTRICT`
- PK `as_requests_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_as_requests_source_consultation_id`: `UNIQUE (source_consultation_id)`

**인덱스**

- `as_requests_pkey`: `CREATE UNIQUE INDEX as_requests_pkey ON public.as_requests USING btree (id)`
- `ix_as_requests_as_code`: `CREATE UNIQUE INDEX ix_as_requests_as_code ON public.as_requests USING btree (as_code)`
- `ix_as_requests_assigned_employee_id`: `CREATE INDEX ix_as_requests_assigned_employee_id ON public.as_requests USING btree (assigned_employee_id)`
- `ix_as_requests_completed_at`: `CREATE INDEX ix_as_requests_completed_at ON public.as_requests USING btree (completed_at)`
- `ix_as_requests_customer_id`: `CREATE INDEX ix_as_requests_customer_id ON public.as_requests USING btree (customer_id)`
- `ix_as_requests_is_deleted`: `CREATE INDEX ix_as_requests_is_deleted ON public.as_requests USING btree (is_deleted)`
- `ix_as_requests_priority`: `CREATE INDEX ix_as_requests_priority ON public.as_requests USING btree (priority)`
- `ix_as_requests_product_id`: `CREATE INDEX ix_as_requests_product_id ON public.as_requests USING btree (product_id)`
- `ix_as_requests_received_at`: `CREATE INDEX ix_as_requests_received_at ON public.as_requests USING btree (received_at)`
- `ix_as_requests_received_store_id`: `CREATE INDEX ix_as_requests_received_store_id ON public.as_requests USING btree (received_store_id)`
- `ix_as_requests_serial_number`: `CREATE INDEX ix_as_requests_serial_number ON public.as_requests USING btree (serial_number)`
- `ix_as_requests_status`: `CREATE INDEX ix_as_requests_status ON public.as_requests USING btree (status)`
- `uq_as_requests_source_consultation_id`: `CREATE UNIQUE INDEX uq_as_requests_source_consultation_id ON public.as_requests USING btree (source_consultation_id)`

### `as_status_histories`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('as_status_histories_id_seq'::regclass)` |
| `as_request_id` | `bigint` | 불가 | — |
| `previous_status` | `character varying(30)` | 허용 | — |
| `new_status` | `character varying(30)` | 불가 | — |
| `changed_by_user_id` | `bigint` | 허용 | — |
| `changed_by_username` | `character varying(50)` | 불가 | — |
| `note` | `character varying(500)` | 허용 | — |
| `changed_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `as_status_histories_as_request_id_fkey`: `FOREIGN KEY (as_request_id) REFERENCES as_requests(id) ON DELETE RESTRICT`
- FK `as_status_histories_changed_by_user_id_fkey`: `FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `as_status_histories_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `as_status_histories_pkey`: `CREATE UNIQUE INDEX as_status_histories_pkey ON public.as_status_histories USING btree (id)`
- `ix_as_status_histories_as_request_id`: `CREATE INDEX ix_as_status_histories_as_request_id ON public.as_status_histories USING btree (as_request_id)`
- `ix_as_status_histories_changed_at`: `CREATE INDEX ix_as_status_histories_changed_at ON public.as_status_histories USING btree (changed_at)`
- `ix_as_status_histories_new_status`: `CREATE INDEX ix_as_status_histories_new_status ON public.as_status_histories USING btree (new_status)`

### `as_symptom_codes`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('as_symptom_codes_id_seq'::regclass)` |
| `symptom_code` | `character varying(50)` | 불가 | — |
| `symptom_name` | `character varying(150)` | 불가 | — |
| `category_code` | `character varying(50)` | 허용 | — |
| `description` | `character varying(500)` | 허용 | — |
| `default_priority` | `character varying(20)` | 불가 | — |
| `requires_serial` | `boolean` | 불가 | — |
| `is_active` | `boolean` | 불가 | — |
| `sort_order` | `integer` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_as_symptom_priority`: `CHECK (default_priority::text = ANY (ARRAY['normal'::character varying, 'important'::character varying, 'urgent'::character varying]::text[]))`
- FK `as_symptom_codes_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `as_symptom_codes_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `as_symptom_codes_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `as_symptom_codes_pkey`: `CREATE UNIQUE INDEX as_symptom_codes_pkey ON public.as_symptom_codes USING btree (id)`
- `ix_as_symptom_active`: `CREATE INDEX ix_as_symptom_active ON public.as_symptom_codes USING btree (is_active)`
- `ix_as_symptom_category`: `CREATE INDEX ix_as_symptom_category ON public.as_symptom_codes USING btree (category_code)`
- `ix_as_symptom_code`: `CREATE UNIQUE INDEX ix_as_symptom_code ON public.as_symptom_codes USING btree (symptom_code)`

### `audit_logs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('audit_logs_id_seq'::regclass)` |
| `actor_user_id` | `bigint` | 허용 | — |
| `actor_username` | `character varying(50)` | 불가 | — |
| `action` | `character varying(30)` | 불가 | — |
| `entity_type` | `character varying(50)` | 불가 | — |
| `entity_id` | `bigint` | 허용 | — |
| `description` | `text` | 불가 | — |
| `before_data` | `jsonb` | 허용 | — |
| `after_data` | `jsonb` | 허용 | — |
| `ip_address` | `character varying(45)` | 허용 | — |
| `occurred_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `audit_logs_actor_user_id_fkey`: `FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `audit_logs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `audit_logs_pkey`: `CREATE UNIQUE INDEX audit_logs_pkey ON public.audit_logs USING btree (id)`
- `ix_audit_logs_action`: `CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action)`
- `ix_audit_logs_actor_user_id`: `CREATE INDEX ix_audit_logs_actor_user_id ON public.audit_logs USING btree (actor_user_id)`
- `ix_audit_logs_entity_id`: `CREATE INDEX ix_audit_logs_entity_id ON public.audit_logs USING btree (entity_id)`
- `ix_audit_logs_entity_type`: `CREATE INDEX ix_audit_logs_entity_type ON public.audit_logs USING btree (entity_type)`
- `ix_audit_logs_occurred_at`: `CREATE INDEX ix_audit_logs_occurred_at ON public.audit_logs USING btree (occurred_at)`

### `batch_job_runs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('batch_job_runs_id_seq'::regclass)` |
| `batch_run_code` | `character varying(30)` | 불가 | — |
| `batch_job_id` | `bigint` | 불가 | — |
| `status` | `character varying(20)` | 불가 | — |
| `trigger_type` | `character varying(20)` | 불가 | — |
| `started_at` | `timestamp with time zone` | 허용 | — |
| `finished_at` | `timestamp with time zone` | 허용 | — |
| `duration_ms` | `bigint` | 허용 | — |
| `result_summary` | `character varying(500)` | 허용 | — |
| `processed_count` | `integer` | 불가 | — |
| `success_count` | `integer` | 불가 | — |
| `failure_count` | `integer` | 불가 | — |
| `error_code` | `character varying(50)` | 허용 | — |
| `error_message` | `character varying(500)` | 허용 | — |
| `triggered_by_user_id` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_batch_run_status`: `CHECK (status::text = ANY (ARRAY['queued'::character varying, 'running'::character varying, 'succeeded'::character varying, 'failed'::character varying, 'cancelled'::character varying]::text[]))`
- CHECK `ck_batch_trigger`: `CHECK (trigger_type::text = ANY (ARRAY['manual'::character varying, 'scheduler'::character varying, 'system'::character varying]::text[]))`
- FK `batch_job_runs_batch_job_id_fkey`: `FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id) ON DELETE RESTRICT`
- FK `batch_job_runs_triggered_by_user_id_fkey`: `FOREIGN KEY (triggered_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `batch_job_runs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `batch_job_runs_pkey`: `CREATE UNIQUE INDEX batch_job_runs_pkey ON public.batch_job_runs USING btree (id)`
- `ix_batch_run_code`: `CREATE UNIQUE INDEX ix_batch_run_code ON public.batch_job_runs USING btree (batch_run_code)`
- `ix_batch_run_job`: `CREATE INDEX ix_batch_run_job ON public.batch_job_runs USING btree (batch_job_id)`
- `ix_batch_run_started`: `CREATE INDEX ix_batch_run_started ON public.batch_job_runs USING btree (started_at)`
- `ix_batch_run_status`: `CREATE INDEX ix_batch_run_status ON public.batch_job_runs USING btree (status)`

### `batch_jobs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('batch_jobs_id_seq'::regclass)` |
| `job_code` | `character varying(50)` | 불가 | — |
| `job_name` | `character varying(150)` | 불가 | — |
| `description` | `character varying(500)` | 허용 | — |
| `job_type` | `character varying(40)` | 불가 | — |
| `schedule_expression` | `character varying(100)` | 허용 | — |
| `is_enabled` | `boolean` | 불가 | — |
| `timeout_seconds` | `integer` | 불가 | — |
| `max_retries` | `integer` | 불가 | — |
| `last_run_at` | `timestamp with time zone` | 허용 | — |
| `next_run_at` | `timestamp with time zone` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_batch_job_type`: `CHECK (job_type::text = ANY (ARRAY['cleanup'::character varying, 'notification'::character varying, 'aggregation'::character varying, 'synchronization_placeholder'::character varying, 'validation'::character varying]::text[]))`
- FK `batch_jobs_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `batch_jobs_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `batch_jobs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `batch_jobs_pkey`: `CREATE UNIQUE INDEX batch_jobs_pkey ON public.batch_jobs USING btree (id)`
- `ix_batch_job_code`: `CREATE UNIQUE INDEX ix_batch_job_code ON public.batch_jobs USING btree (job_code)`
- `ix_batch_job_enabled`: `CREATE INDEX ix_batch_job_enabled ON public.batch_jobs USING btree (is_enabled)`
- `ix_batch_job_type`: `CREATE INDEX ix_batch_job_type ON public.batch_jobs USING btree (job_type)`

### `common_code_groups`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('common_code_groups_id_seq'::regclass)` |
| `group_code` | `character varying(50)` | 불가 | — |
| `group_name` | `character varying(100)` | 불가 | — |
| `description` | `character varying(500)` | 허용 | — |
| `is_system` | `boolean` | 불가 | — |
| `is_active` | `boolean` | 불가 | — |
| `sort_order` | `integer` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- FK `common_code_groups_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `common_code_groups_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `common_code_groups_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `common_code_groups_pkey`: `CREATE UNIQUE INDEX common_code_groups_pkey ON public.common_code_groups USING btree (id)`
- `ix_common_code_groups_active`: `CREATE INDEX ix_common_code_groups_active ON public.common_code_groups USING btree (is_active)`
- `ix_common_code_groups_code`: `CREATE UNIQUE INDEX ix_common_code_groups_code ON public.common_code_groups USING btree (group_code)`
- `ix_common_code_groups_sort`: `CREATE INDEX ix_common_code_groups_sort ON public.common_code_groups USING btree (sort_order)`

### `common_codes`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('common_codes_id_seq'::regclass)` |
| `group_id` | `bigint` | 불가 | — |
| `code` | `character varying(50)` | 불가 | — |
| `name` | `character varying(100)` | 불가 | — |
| `description` | `character varying(500)` | 허용 | — |
| `extra_value` | `json` | 허용 | — |
| `is_default` | `boolean` | 불가 | — |
| `is_active` | `boolean` | 불가 | — |
| `sort_order` | `integer` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- FK `common_codes_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `common_codes_group_id_fkey`: `FOREIGN KEY (group_id) REFERENCES common_code_groups(id) ON DELETE RESTRICT`
- FK `common_codes_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `common_codes_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_common_codes_group_code`: `UNIQUE (group_id, code)`

**인덱스**

- `common_codes_pkey`: `CREATE UNIQUE INDEX common_codes_pkey ON public.common_codes USING btree (id)`
- `ix_common_codes_active`: `CREATE INDEX ix_common_codes_active ON public.common_codes USING btree (is_active)`
- `ix_common_codes_group`: `CREATE INDEX ix_common_codes_group ON public.common_codes USING btree (group_id)`
- `ix_common_codes_sort`: `CREATE INDEX ix_common_codes_sort ON public.common_codes USING btree (sort_order)`
- `uq_common_codes_group_code`: `CREATE UNIQUE INDEX uq_common_codes_group_code ON public.common_codes USING btree (group_id, code)`
- `uq_common_codes_one_default`: `CREATE UNIQUE INDEX uq_common_codes_one_default ON public.common_codes USING btree (group_id) WHERE (is_default = true)`

### `consultation_notes`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('consultation_notes_id_seq'::regclass)` |
| `consultation_id` | `bigint` | 불가 | — |
| `author_user_id` | `bigint` | 허용 | — |
| `author_username` | `character varying(50)` | 불가 | — |
| `content` | `text` | 불가 | — |
| `is_internal` | `boolean` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `consultation_notes_author_user_id_fkey`: `FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `consultation_notes_consultation_id_fkey`: `FOREIGN KEY (consultation_id) REFERENCES consultations(id) ON DELETE RESTRICT`
- PK `consultation_notes_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `consultation_notes_pkey`: `CREATE UNIQUE INDEX consultation_notes_pkey ON public.consultation_notes USING btree (id)`
- `ix_consultation_notes_consultation_id`: `CREATE INDEX ix_consultation_notes_consultation_id ON public.consultation_notes USING btree (consultation_id)`
- `ix_consultation_notes_created_at`: `CREATE INDEX ix_consultation_notes_created_at ON public.consultation_notes USING btree (created_at)`

### `consultations`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('consultations_id_seq'::regclass)` |
| `consultation_code` | `character varying(30)` | 불가 | — |
| `customer_id` | `bigint` | 불가 | — |
| `assigned_employee_id` | `bigint` | 허용 | — |
| `consultation_type` | `character varying(50)` | 불가 | — |
| `channel` | `character varying(30)` | 불가 | — |
| `title` | `character varying(200)` | 불가 | — |
| `content` | `text` | 불가 | — |
| `status` | `character varying(30)` | 불가 | — |
| `priority` | `character varying(20)` | 불가 | — |
| `completed_at` | `timestamp with time zone` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_consultations_priority`: `CHECK (priority::text = ANY (ARRAY['low'::character varying, 'normal'::character varying, 'high'::character varying, 'urgent'::character varying]::text[]))`
- CHECK `ck_consultations_status`: `CHECK (status::text = ANY (ARRAY['received'::character varying, 'in_progress'::character varying, 'waiting'::character varying, 'transferred_to_as'::character varying, 'completed'::character varying, 'cancelled'::character varying]::text[]))`
- FK `consultations_assigned_employee_id_fkey`: `FOREIGN KEY (assigned_employee_id) REFERENCES employees(id) ON DELETE SET NULL`
- FK `consultations_customer_id_fkey`: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT`
- FK `consultations_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `consultations_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `consultations_pkey`: `CREATE UNIQUE INDEX consultations_pkey ON public.consultations USING btree (id)`
- `ix_consultations_assigned_employee_id`: `CREATE INDEX ix_consultations_assigned_employee_id ON public.consultations USING btree (assigned_employee_id)`
- `ix_consultations_consultation_code`: `CREATE UNIQUE INDEX ix_consultations_consultation_code ON public.consultations USING btree (consultation_code)`
- `ix_consultations_consultation_type`: `CREATE INDEX ix_consultations_consultation_type ON public.consultations USING btree (consultation_type)`
- `ix_consultations_created_at`: `CREATE INDEX ix_consultations_created_at ON public.consultations USING btree (created_at)`
- `ix_consultations_customer_id`: `CREATE INDEX ix_consultations_customer_id ON public.consultations USING btree (customer_id)`
- `ix_consultations_is_deleted`: `CREATE INDEX ix_consultations_is_deleted ON public.consultations USING btree (is_deleted)`
- `ix_consultations_priority`: `CREATE INDEX ix_consultations_priority ON public.consultations USING btree (priority)`
- `ix_consultations_status`: `CREATE INDEX ix_consultations_status ON public.consultations USING btree (status)`

### `customers`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('customers_id_seq'::regclass)` |
| `customer_code` | `character varying(30)` | 불가 | — |
| `name` | `character varying(100)` | 불가 | — |
| `phone` | `character varying(30)` | 허용 | — |
| `phone_normalized` | `character varying(30)` | 허용 | — |
| `secondary_phone` | `character varying(30)` | 허용 | — |
| `email` | `character varying(255)` | 허용 | — |
| `birth_date` | `date` | 허용 | — |
| `gender` | `character varying(20)` | 허용 | — |
| `postal_code` | `character varying(20)` | 허용 | — |
| `address` | `character varying(500)` | 허용 | — |
| `address_detail` | `character varying(500)` | 허용 | — |
| `marketing_sms_consent` | `boolean` | 불가 | — |
| `marketing_email_consent` | `boolean` | 불가 | — |
| `memo` | `text` | 허용 | — |
| `status` | `character varying(20)` | 불가 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |
| `is_vip` | `boolean` | 불가 | `false` |
| `vip_level` | `character varying(20)` | 허용 | — |
| `vip_memo` | `character varying(500)` | 허용 | — |
| `vip_updated_at` | `timestamp with time zone` | 허용 | — |

**제약조건**

- CHECK `ck_customers_gender`: `CHECK (gender IS NULL OR (gender::text = ANY (ARRAY['male'::character varying, 'female'::character varying, 'unknown'::character varying]::text[])))`
- CHECK `ck_customers_status`: `CHECK (status::text = ANY (ARRAY['active'::character varying, 'inactive'::character varying]::text[]))`
- CHECK `ck_customers_vip_level`: `CHECK (vip_level IS NULL OR (vip_level::text = ANY (ARRAY['vip'::character varying, 'vvip'::character varying]::text[])))`
- FK `customers_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `customers_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `customers_pkey`: `CREATE UNIQUE INDEX customers_pkey ON public.customers USING btree (id)`
- `ix_customers_created_at`: `CREATE INDEX ix_customers_created_at ON public.customers USING btree (created_at)`
- `ix_customers_customer_code`: `CREATE UNIQUE INDEX ix_customers_customer_code ON public.customers USING btree (customer_code)`
- `ix_customers_email`: `CREATE INDEX ix_customers_email ON public.customers USING btree (email)`
- `ix_customers_is_deleted`: `CREATE INDEX ix_customers_is_deleted ON public.customers USING btree (is_deleted)`
- `ix_customers_is_vip`: `CREATE INDEX ix_customers_is_vip ON public.customers USING btree (is_vip)`
- `ix_customers_name`: `CREATE INDEX ix_customers_name ON public.customers USING btree (name)`
- `ix_customers_phone_normalized`: `CREATE INDEX ix_customers_phone_normalized ON public.customers USING btree (phone_normalized)`
- `ix_customers_status`: `CREATE INDEX ix_customers_status ON public.customers USING btree (status)`

### `employees`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('employees_id_seq'::regclass)` |
| `employee_code` | `character varying(30)` | 불가 | — |
| `user_id` | `bigint` | 허용 | — |
| `store_id` | `bigint` | 불가 | — |
| `name` | `character varying(100)` | 불가 | — |
| `position` | `character varying(50)` | 불가 | — |
| `phone` | `character varying(30)` | 허용 | — |
| `email` | `character varying(255)` | 허용 | — |
| `joined_at` | `date` | 불가 | — |
| `resigned_at` | `date` | 허용 | — |
| `resignation_reason` | `character varying(500)` | 허용 | — |
| `employment_status` | `character varying(20)` | 불가 | — |
| `approval_status` | `character varying(20)` | 불가 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_employees_approval_status`: `CHECK (approval_status::text = ANY (ARRAY['pending'::character varying, 'approved'::character varying]::text[]))`
- CHECK `ck_employees_employment_status`: `CHECK (employment_status::text = ANY (ARRAY['active'::character varying, 'resigned'::character varying]::text[]))`
- FK `employees_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `employees_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- FK `employees_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `employees_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_employees_user_id`: `UNIQUE (user_id)`

**인덱스**

- `employees_pkey`: `CREATE UNIQUE INDEX employees_pkey ON public.employees USING btree (id)`
- `ix_employees_approval_status`: `CREATE INDEX ix_employees_approval_status ON public.employees USING btree (approval_status)`
- `ix_employees_created_at`: `CREATE INDEX ix_employees_created_at ON public.employees USING btree (created_at)`
- `ix_employees_employee_code`: `CREATE UNIQUE INDEX ix_employees_employee_code ON public.employees USING btree (employee_code)`
- `ix_employees_employment_status`: `CREATE INDEX ix_employees_employment_status ON public.employees USING btree (employment_status)`
- `ix_employees_is_deleted`: `CREATE INDEX ix_employees_is_deleted ON public.employees USING btree (is_deleted)`
- `ix_employees_name`: `CREATE INDEX ix_employees_name ON public.employees USING btree (name)`
- `ix_employees_store_id`: `CREATE INDEX ix_employees_store_id ON public.employees USING btree (store_id)`
- `ix_employees_user_id`: `CREATE INDEX ix_employees_user_id ON public.employees USING btree (user_id)`
- `uq_employees_user_id`: `CREATE UNIQUE INDEX uq_employees_user_id ON public.employees USING btree (user_id)`

### `goods_receipt_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('goods_receipt_items_id_seq'::regclass)` |
| `goods_receipt_id` | `bigint` | 불가 | — |
| `purchase_order_item_id` | `bigint` | 허용 | — |
| `product_id` | `bigint` | 불가 | — |
| `product_code_snapshot` | `character varying(50)` | 불가 | — |
| `product_name_snapshot` | `character varying(200)` | 불가 | — |
| `quantity` | `integer` | 불가 | — |
| `unit_cost` | `numeric(14,2)` | 불가 | — |
| `serial_number` | `character varying(150)` | 허용 | — |
| `memo` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_receipt_items_quantity`: `CHECK (quantity >= 1)`
- FK `goods_receipt_items_goods_receipt_id_fkey`: `FOREIGN KEY (goods_receipt_id) REFERENCES goods_receipts(id) ON DELETE CASCADE`
- FK `goods_receipt_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `goods_receipt_items_purchase_order_item_id_fkey`: `FOREIGN KEY (purchase_order_item_id) REFERENCES purchase_order_items(id) ON DELETE RESTRICT`
- PK `goods_receipt_items_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_receipt_serial`: `UNIQUE (goods_receipt_id, serial_number)`

**인덱스**

- `goods_receipt_items_pkey`: `CREATE UNIQUE INDEX goods_receipt_items_pkey ON public.goods_receipt_items USING btree (id)`
- `ix_receipt_items_product`: `CREATE INDEX ix_receipt_items_product ON public.goods_receipt_items USING btree (product_id)`
- `ix_receipt_items_receipt`: `CREATE INDEX ix_receipt_items_receipt ON public.goods_receipt_items USING btree (goods_receipt_id)`
- `ix_receipt_items_serial`: `CREATE INDEX ix_receipt_items_serial ON public.goods_receipt_items USING btree (serial_number)`
- `uq_receipt_serial`: `CREATE UNIQUE INDEX uq_receipt_serial ON public.goods_receipt_items USING btree (goods_receipt_id, serial_number)`

### `goods_receipts`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('goods_receipts_id_seq'::regclass)` |
| `goods_receipt_code` | `character varying(30)` | 불가 | — |
| `purchase_order_id` | `bigint` | 허용 | — |
| `store_id` | `bigint` | 불가 | — |
| `receipt_type` | `character varying(30)` | 불가 | — |
| `received_at` | `timestamp with time zone` | 불가 | — |
| `received_by_employee_id` | `bigint` | 허용 | — |
| `status` | `character varying(20)` | 불가 | — |
| `supplier_name` | `character varying(150)` | 허용 | — |
| `reference_number` | `character varying(100)` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `completed_at` | `timestamp with time zone` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `cancellation_reason` | `character varying(500)` | 허용 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_receipts_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'completed'::character varying, 'cancelled'::character varying]::text[]))`
- CHECK `ck_receipts_type`: `CHECK (receipt_type::text = ANY (ARRAY['purchase_order'::character varying, 'direct'::character varying, 'return'::character varying, 'adjustment'::character varying]::text[]))`
- FK `goods_receipts_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `goods_receipts_purchase_order_id_fkey`: `FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE RESTRICT`
- FK `goods_receipts_received_by_employee_id_fkey`: `FOREIGN KEY (received_by_employee_id) REFERENCES employees(id) ON DELETE SET NULL`
- FK `goods_receipts_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `goods_receipts_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `goods_receipts_pkey`: `CREATE UNIQUE INDEX goods_receipts_pkey ON public.goods_receipts USING btree (id)`
- `ix_receipts_code`: `CREATE UNIQUE INDEX ix_receipts_code ON public.goods_receipts USING btree (goods_receipt_code)`
- `ix_receipts_po`: `CREATE INDEX ix_receipts_po ON public.goods_receipts USING btree (purchase_order_id)`
- `ix_receipts_status`: `CREATE INDEX ix_receipts_status ON public.goods_receipts USING btree (status)`
- `ix_receipts_store`: `CREATE INDEX ix_receipts_store ON public.goods_receipts USING btree (store_id)`

### `inventory_adjustment_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('inventory_adjustment_items_id_seq'::regclass)` |
| `inventory_adjustment_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `adjustment_quantity` | `integer` | 불가 | — |
| `serial_number` | `character varying(150)` | 허용 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_adjustment_items_nonzero`: `CHECK (adjustment_quantity <> 0)`
- FK `inventory_adjustment_items_inventory_adjustment_id_fkey`: `FOREIGN KEY (inventory_adjustment_id) REFERENCES inventory_adjustments(id) ON DELETE CASCADE`
- FK `inventory_adjustment_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- PK `inventory_adjustment_items_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `inventory_adjustment_items_pkey`: `CREATE UNIQUE INDEX inventory_adjustment_items_pkey ON public.inventory_adjustment_items USING btree (id)`

### `inventory_adjustments`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('inventory_adjustments_id_seq'::regclass)` |
| `adjustment_code` | `character varying(30)` | 불가 | — |
| `store_id` | `bigint` | 불가 | — |
| `status` | `character varying(20)` | 불가 | — |
| `reason` | `character varying(500)` | 불가 | — |
| `requested_by_user_id` | `bigint` | 불가 | — |
| `approved_by_user_id` | `bigint` | 허용 | — |
| `applied_at` | `timestamp with time zone` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_adjustment_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'requested'::character varying, 'approved'::character varying, 'applied'::character varying, 'rejected'::character varying, 'cancelled'::character varying]::text[]))`
- FK `inventory_adjustments_approved_by_user_id_fkey`: `FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `inventory_adjustments_requested_by_user_id_fkey`: `FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- FK `inventory_adjustments_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `inventory_adjustments_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `inventory_adjustments_pkey`: `CREATE UNIQUE INDEX inventory_adjustments_pkey ON public.inventory_adjustments USING btree (id)`
- `ix_adjustment_code`: `CREATE UNIQUE INDEX ix_adjustment_code ON public.inventory_adjustments USING btree (adjustment_code)`
- `ix_adjustment_status`: `CREATE INDEX ix_adjustment_status ON public.inventory_adjustments USING btree (status)`
- `ix_adjustment_store`: `CREATE INDEX ix_adjustment_store ON public.inventory_adjustments USING btree (store_id)`

### `inventory_balances`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('inventory_balances_id_seq'::regclass)` |
| `store_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `current_quantity` | `integer` | 불가 | — |
| `reserved_quantity` | `integer` | 불가 | — |
| `last_movement_at` | `timestamp with time zone` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_inventory_nonnegative`: `CHECK (current_quantity >= 0 AND reserved_quantity >= 0 AND reserved_quantity <= current_quantity)`
- FK `inventory_balances_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `inventory_balances_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `inventory_balances_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_inventory_store_product`: `UNIQUE (store_id, product_id)`

**인덱스**

- `inventory_balances_pkey`: `CREATE UNIQUE INDEX inventory_balances_pkey ON public.inventory_balances USING btree (id)`
- `ix_inventory_product`: `CREATE INDEX ix_inventory_product ON public.inventory_balances USING btree (product_id)`
- `ix_inventory_quantity`: `CREATE INDEX ix_inventory_quantity ON public.inventory_balances USING btree (current_quantity)`
- `ix_inventory_store`: `CREATE INDEX ix_inventory_store ON public.inventory_balances USING btree (store_id)`
- `uq_inventory_store_product`: `CREATE UNIQUE INDEX uq_inventory_store_product ON public.inventory_balances USING btree (store_id, product_id)`

### `inventory_movements`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('inventory_movements_id_seq'::regclass)` |
| `store_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `serial_number` | `character varying(150)` | 허용 | — |
| `movement_type` | `character varying(30)` | 불가 | — |
| `quantity_change` | `integer` | 불가 | — |
| `quantity_before` | `integer` | 불가 | — |
| `quantity_after` | `integer` | 불가 | — |
| `source_type` | `character varying(30)` | 불가 | — |
| `source_id` | `bigint` | 불가 | — |
| `source_code` | `character varying(30)` | 불가 | — |
| `reference_store_id` | `bigint` | 허용 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `performed_by_user_id` | `bigint` | 허용 | — |
| `performed_by_username` | `character varying(50)` | 불가 | — |
| `occurred_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_movement_nonzero`: `CHECK (quantity_change <> 0)`
- FK `inventory_movements_performed_by_user_id_fkey`: `FOREIGN KEY (performed_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `inventory_movements_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `inventory_movements_reference_store_id_fkey`: `FOREIGN KEY (reference_store_id) REFERENCES stores(id) ON DELETE SET NULL`
- FK `inventory_movements_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `inventory_movements_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `inventory_movements_pkey`: `CREATE UNIQUE INDEX inventory_movements_pkey ON public.inventory_movements USING btree (id)`
- `ix_movements_occurred`: `CREATE INDEX ix_movements_occurred ON public.inventory_movements USING btree (occurred_at)`
- `ix_movements_product`: `CREATE INDEX ix_movements_product ON public.inventory_movements USING btree (product_id)`
- `ix_movements_serial`: `CREATE INDEX ix_movements_serial ON public.inventory_movements USING btree (serial_number)`
- `ix_movements_source`: `CREATE INDEX ix_movements_source ON public.inventory_movements USING btree (source_type, source_id)`
- `ix_movements_store`: `CREATE INDEX ix_movements_store ON public.inventory_movements USING btree (store_id)`
- `ix_movements_type`: `CREATE INDEX ix_movements_type ON public.inventory_movements USING btree (movement_type)`

### `login_logs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('login_logs_id_seq'::regclass)` |
| `user_id` | `bigint` | 허용 | — |
| `username` | `character varying(50)` | 불가 | — |
| `result` | `character varying(20)` | 불가 | — |
| `failure_reason` | `character varying(50)` | 허용 | — |
| `ip_address` | `character varying(45)` | 허용 | — |
| `user_agent` | `character varying(500)` | 허용 | — |
| `occurred_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_login_logs_result`: `CHECK (result::text = ANY (ARRAY['success'::character varying, 'failure'::character varying]::text[]))`
- FK `login_logs_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `login_logs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_login_logs_occurred_at`: `CREATE INDEX ix_login_logs_occurred_at ON public.login_logs USING btree (occurred_at)`
- `ix_login_logs_result`: `CREATE INDEX ix_login_logs_result ON public.login_logs USING btree (result)`
- `ix_login_logs_user_id`: `CREATE INDEX ix_login_logs_user_id ON public.login_logs USING btree (user_id)`
- `ix_login_logs_username`: `CREATE INDEX ix_login_logs_username ON public.login_logs USING btree (username)`
- `login_logs_pkey`: `CREATE UNIQUE INDEX login_logs_pkey ON public.login_logs USING btree (id)`

### `logistics_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('logistics_items_id_seq'::regclass)` |
| `logistics_order_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `product_code_snapshot` | `character varying(50)` | 불가 | — |
| `product_name_snapshot` | `character varying(200)` | 불가 | — |
| `model_name_snapshot` | `character varying(150)` | 허용 | — |
| `quantity` | `integer` | 불가 | — |
| `serial_number` | `character varying(150)` | 허용 | — |
| `item_status` | `character varying(20)` | 불가 | `'pending'::character varying` |
| `memo` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `inventory_action` | `character varying(20)` | 불가 | `'no_effect'::character varying` |

**제약조건**

- CHECK `ck_logistics_items_inventory_action`: `CHECK (inventory_action::text = ANY (ARRAY['issue'::character varying, 'transfer'::character varying, 'no_effect'::character varying]::text[]))`
- CHECK `ck_logistics_items_quantity`: `CHECK (quantity >= 1)`
- CHECK `ck_logistics_items_status`: `CHECK (item_status::text = ANY (ARRAY['pending'::character varying, 'prepared'::character varying, 'shipped'::character varying, 'cancelled'::character varying]::text[]))`
- FK `logistics_items_logistics_order_id_fkey`: `FOREIGN KEY (logistics_order_id) REFERENCES logistics_orders(id) ON DELETE CASCADE`
- FK `logistics_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- PK `logistics_items_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_logistics_items_order_serial`: `UNIQUE (logistics_order_id, serial_number)`

**인덱스**

- `ix_logistics_items_order_id`: `CREATE INDEX ix_logistics_items_order_id ON public.logistics_items USING btree (logistics_order_id)`
- `ix_logistics_items_product_id`: `CREATE INDEX ix_logistics_items_product_id ON public.logistics_items USING btree (product_id)`
- `ix_logistics_items_serial`: `CREATE INDEX ix_logistics_items_serial ON public.logistics_items USING btree (serial_number)`
- `ix_logistics_items_status`: `CREATE INDEX ix_logistics_items_status ON public.logistics_items USING btree (item_status)`
- `logistics_items_pkey`: `CREATE UNIQUE INDEX logistics_items_pkey ON public.logistics_items USING btree (id)`
- `uq_logistics_items_order_serial`: `CREATE UNIQUE INDEX uq_logistics_items_order_serial ON public.logistics_items USING btree (logistics_order_id, serial_number)`

### `logistics_notes`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('logistics_notes_id_seq'::regclass)` |
| `logistics_order_id` | `bigint` | 불가 | — |
| `author_user_id` | `bigint` | 허용 | — |
| `author_username` | `character varying(50)` | 불가 | — |
| `note_type` | `character varying(30)` | 불가 | — |
| `content` | `text` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_logistics_notes_type`: `CHECK (note_type::text = ANY (ARRAY['general'::character varying, 'preparation'::character varying, 'customer_contact'::character varying, 'shipping'::character varying, 'delivery'::character varying, 'issue'::character varying]::text[]))`
- FK `logistics_notes_author_user_id_fkey`: `FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `logistics_notes_logistics_order_id_fkey`: `FOREIGN KEY (logistics_order_id) REFERENCES logistics_orders(id) ON DELETE CASCADE`
- PK `logistics_notes_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_logistics_notes_created_at`: `CREATE INDEX ix_logistics_notes_created_at ON public.logistics_notes USING btree (created_at)`
- `ix_logistics_notes_order_id`: `CREATE INDEX ix_logistics_notes_order_id ON public.logistics_notes USING btree (logistics_order_id)`
- `ix_logistics_notes_type`: `CREATE INDEX ix_logistics_notes_type ON public.logistics_notes USING btree (note_type)`
- `logistics_notes_pkey`: `CREATE UNIQUE INDEX logistics_notes_pkey ON public.logistics_notes USING btree (id)`

### `logistics_orders`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('logistics_orders_id_seq'::regclass)` |
| `logistics_code` | `character varying(30)` | 불가 | — |
| `source_type` | `character varying(20)` | 불가 | — |
| `source_sale_id` | `bigint` | 허용 | — |
| `source_as_request_id` | `bigint` | 허용 | — |
| `logistics_type` | `character varying(30)` | 불가 | — |
| `customer_id` | `bigint` | 허용 | — |
| `origin_store_id` | `bigint` | 허용 | — |
| `destination_store_id` | `bigint` | 허용 | — |
| `assigned_employee_id` | `bigint` | 허용 | — |
| `requested_by_user_id` | `bigint` | 불가 | — |
| `status` | `character varying(30)` | 불가 | `'requested'::character varying` |
| `request_date` | `timestamp with time zone` | 불가 | — |
| `expected_ship_date` | `date` | 허용 | — |
| `shipped_at` | `timestamp with time zone` | 허용 | — |
| `delivered_at` | `timestamp with time zone` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `cancellation_reason` | `character varying(500)` | 허용 | — |
| `recipient_name` | `character varying(100)` | 허용 | — |
| `recipient_phone` | `character varying(30)` | 허용 | — |
| `postal_code` | `character varying(20)` | 허용 | — |
| `shipping_address` | `character varying(500)` | 허용 | — |
| `shipping_address_detail` | `character varying(500)` | 허용 | — |
| `request_memo` | `text` | 허용 | — |
| `is_deleted` | `boolean` | 불가 | `false` |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_logistics_source_type`: `CHECK (source_type::text = ANY (ARRAY['direct'::character varying, 'sale'::character varying, 'as_request'::character varying]::text[]))`
- CHECK `ck_logistics_status`: `CHECK (status::text = ANY (ARRAY['requested'::character varying, 'preparing'::character varying, 'ready_to_ship'::character varying, 'shipped'::character varying, 'in_transit'::character varying, 'delivered'::character varying, 'cancelled'::character varying]::text[]))`
- CHECK `ck_logistics_type`: `CHECK (logistics_type::text = ANY (ARRAY['customer_delivery'::character varying, 'store_transfer'::character varying, 'as_return'::character varying, 'exchange'::character varying, 'sample'::character varying, 'other'::character varying]::text[]))`
- FK `logistics_orders_assigned_employee_id_fkey`: `FOREIGN KEY (assigned_employee_id) REFERENCES employees(id) ON DELETE SET NULL`
- FK `logistics_orders_customer_id_fkey`: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT`
- FK `logistics_orders_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `logistics_orders_destination_store_id_fkey`: `FOREIGN KEY (destination_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- FK `logistics_orders_origin_store_id_fkey`: `FOREIGN KEY (origin_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- FK `logistics_orders_requested_by_user_id_fkey`: `FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- FK `logistics_orders_source_as_request_id_fkey`: `FOREIGN KEY (source_as_request_id) REFERENCES as_requests(id) ON DELETE RESTRICT`
- FK `logistics_orders_source_sale_id_fkey`: `FOREIGN KEY (source_sale_id) REFERENCES sales(id) ON DELETE RESTRICT`
- PK `logistics_orders_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_logistics_orders_code`: `CREATE UNIQUE INDEX ix_logistics_orders_code ON public.logistics_orders USING btree (logistics_code)`
- `ix_logistics_orders_customer_id`: `CREATE INDEX ix_logistics_orders_customer_id ON public.logistics_orders USING btree (customer_id)`
- `ix_logistics_orders_delivered_at`: `CREATE INDEX ix_logistics_orders_delivered_at ON public.logistics_orders USING btree (delivered_at)`
- `ix_logistics_orders_destination_store_id`: `CREATE INDEX ix_logistics_orders_destination_store_id ON public.logistics_orders USING btree (destination_store_id)`
- `ix_logistics_orders_employee_id`: `CREATE INDEX ix_logistics_orders_employee_id ON public.logistics_orders USING btree (assigned_employee_id)`
- `ix_logistics_orders_is_deleted`: `CREATE INDEX ix_logistics_orders_is_deleted ON public.logistics_orders USING btree (is_deleted)`
- `ix_logistics_orders_origin_store_id`: `CREATE INDEX ix_logistics_orders_origin_store_id ON public.logistics_orders USING btree (origin_store_id)`
- `ix_logistics_orders_request_date`: `CREATE INDEX ix_logistics_orders_request_date ON public.logistics_orders USING btree (request_date)`
- `ix_logistics_orders_shipped_at`: `CREATE INDEX ix_logistics_orders_shipped_at ON public.logistics_orders USING btree (shipped_at)`
- `ix_logistics_orders_source_as_request_id`: `CREATE UNIQUE INDEX ix_logistics_orders_source_as_request_id ON public.logistics_orders USING btree (source_as_request_id) WHERE (source_as_request_id IS NOT NULL)`
- `ix_logistics_orders_source_sale_id`: `CREATE UNIQUE INDEX ix_logistics_orders_source_sale_id ON public.logistics_orders USING btree (source_sale_id) WHERE (source_sale_id IS NOT NULL)`
- `ix_logistics_orders_source_type`: `CREATE INDEX ix_logistics_orders_source_type ON public.logistics_orders USING btree (source_type)`
- `ix_logistics_orders_status`: `CREATE INDEX ix_logistics_orders_status ON public.logistics_orders USING btree (status)`
- `ix_logistics_orders_type`: `CREATE INDEX ix_logistics_orders_type ON public.logistics_orders USING btree (logistics_type)`
- `logistics_orders_pkey`: `CREATE UNIQUE INDEX logistics_orders_pkey ON public.logistics_orders USING btree (id)`

### `logistics_status_histories`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('logistics_status_histories_id_seq'::regclass)` |
| `logistics_order_id` | `bigint` | 불가 | — |
| `previous_status` | `character varying(30)` | 허용 | — |
| `new_status` | `character varying(30)` | 불가 | — |
| `changed_by_user_id` | `bigint` | 허용 | — |
| `changed_by_username` | `character varying(50)` | 불가 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `changed_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `logistics_status_histories_changed_by_user_id_fkey`: `FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `logistics_status_histories_logistics_order_id_fkey`: `FOREIGN KEY (logistics_order_id) REFERENCES logistics_orders(id) ON DELETE CASCADE`
- PK `logistics_status_histories_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_logistics_histories_changed_at`: `CREATE INDEX ix_logistics_histories_changed_at ON public.logistics_status_histories USING btree (changed_at)`
- `ix_logistics_histories_order_id`: `CREATE INDEX ix_logistics_histories_order_id ON public.logistics_status_histories USING btree (logistics_order_id)`
- `ix_logistics_histories_status`: `CREATE INDEX ix_logistics_histories_status ON public.logistics_status_histories USING btree (new_status)`
- `logistics_status_histories_pkey`: `CREATE UNIQUE INDEX logistics_status_histories_pkey ON public.logistics_status_histories USING btree (id)`

### `marketplaces`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('marketplaces_id_seq'::regclass)` |
| `code` | `character varying(50)` | 불가 | — |
| `name` | `character varying(100)` | 불가 | — |
| `marketplace_type` | `character varying(50)` | 허용 | — |
| `description` | `character varying(500)` | 허용 | — |
| `status` | `character varying(20)` | 불가 | `'active'::character varying` |
| `sort_order` | `integer` | 불가 | `0` |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_marketplaces_sort_order_nonnegative`: `CHECK (sort_order >= 0)`
- CHECK `ck_marketplaces_status`: `CHECK (status::text = ANY (ARRAY['active'::character varying, 'inactive'::character varying]::text[]))`
- PK `marketplaces_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_marketplaces_code`: `CREATE UNIQUE INDEX ix_marketplaces_code ON public.marketplaces USING btree (code)`
- `ix_marketplaces_name`: `CREATE UNIQUE INDEX ix_marketplaces_name ON public.marketplaces USING btree (name)`
- `ix_marketplaces_sort_order`: `CREATE INDEX ix_marketplaces_sort_order ON public.marketplaces USING btree (sort_order)`
- `ix_marketplaces_status`: `CREATE INDEX ix_marketplaces_status ON public.marketplaces USING btree (status)`
- `ix_marketplaces_type`: `CREATE INDEX ix_marketplaces_type ON public.marketplaces USING btree (marketplace_type)`
- `marketplaces_pkey`: `CREATE UNIQUE INDEX marketplaces_pkey ON public.marketplaces USING btree (id)`

### `memos`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('memos_id_seq'::regclass)` |
| `title` | `character varying(200)` | 허용 | — |
| `content` | `text` | 불가 | — |
| `memo_type` | `character varying(20)` | 불가 | — |
| `target_store_id` | `bigint` | 허용 | — |
| `entity_type` | `character varying(30)` | 불가 | — |
| `entity_id` | `bigint` | 허용 | — |
| `author_user_id` | `bigint` | 불가 | — |
| `author_username` | `character varying(50)` | 불가 | — |
| `is_pinned` | `boolean` | 불가 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_memos_entity_type`: `CHECK (entity_type::text = ANY (ARRAY['general'::character varying, 'customer'::character varying, 'consultation'::character varying, 'as_request'::character varying, 'sale'::character varying, 'logistics_order'::character varying, 'purchase_order'::character varying, 'goods_receipt'::character varying, 'stock_transfer'::character varying, 'inventory_adjustment'::character varying]::text[]))`
- CHECK `ck_memos_type`: `CHECK (memo_type::text = ANY (ARRAY['personal'::character varying, 'shared'::character varying, 'store'::character varying]::text[]))`
- FK `memos_author_user_id_fkey`: `FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- FK `memos_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `memos_target_store_id_fkey`: `FOREIGN KEY (target_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `memos_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_memos_author_user_id`: `CREATE INDEX ix_memos_author_user_id ON public.memos USING btree (author_user_id)`
- `ix_memos_created_at`: `CREATE INDEX ix_memos_created_at ON public.memos USING btree (created_at)`
- `ix_memos_entity_id`: `CREATE INDEX ix_memos_entity_id ON public.memos USING btree (entity_id)`
- `ix_memos_entity_type`: `CREATE INDEX ix_memos_entity_type ON public.memos USING btree (entity_type)`
- `ix_memos_is_deleted`: `CREATE INDEX ix_memos_is_deleted ON public.memos USING btree (is_deleted)`
- `ix_memos_is_pinned`: `CREATE INDEX ix_memos_is_pinned ON public.memos USING btree (is_pinned)`
- `ix_memos_memo_type`: `CREATE INDEX ix_memos_memo_type ON public.memos USING btree (memo_type)`
- `ix_memos_target_store_id`: `CREATE INDEX ix_memos_target_store_id ON public.memos USING btree (target_store_id)`
- `memos_pkey`: `CREATE UNIQUE INDEX memos_pkey ON public.memos USING btree (id)`

### `notice_reads`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('notice_reads_id_seq'::regclass)` |
| `notice_id` | `bigint` | 불가 | — |
| `user_id` | `bigint` | 불가 | — |
| `first_read_at` | `timestamp with time zone` | 불가 | — |
| `last_read_at` | `timestamp with time zone` | 불가 | — |
| `read_count` | `integer` | 불가 | — |

**제약조건**

- CHECK `ck_notice_reads_read_count`: `CHECK (read_count >= 1)`
- FK `notice_reads_notice_id_fkey`: `FOREIGN KEY (notice_id) REFERENCES notices(id) ON DELETE CASCADE`
- FK `notice_reads_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- PK `notice_reads_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_notice_reads_notice_user`: `UNIQUE (notice_id, user_id)`

**인덱스**

- `ix_notice_reads_first_read_at`: `CREATE INDEX ix_notice_reads_first_read_at ON public.notice_reads USING btree (first_read_at)`
- `ix_notice_reads_user_id`: `CREATE INDEX ix_notice_reads_user_id ON public.notice_reads USING btree (user_id)`
- `notice_reads_pkey`: `CREATE UNIQUE INDEX notice_reads_pkey ON public.notice_reads USING btree (id)`
- `uq_notice_reads_notice_user`: `CREATE UNIQUE INDEX uq_notice_reads_notice_user ON public.notice_reads USING btree (notice_id, user_id)`

### `notices`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('notices_id_seq'::regclass)` |
| `title` | `character varying(200)` | 불가 | — |
| `content` | `text` | 불가 | — |
| `status` | `character varying(20)` | 불가 | — |
| `priority` | `character varying(20)` | 불가 | — |
| `visibility_type` | `character varying(20)` | 불가 | — |
| `target_store_id` | `bigint` | 허용 | — |
| `target_role` | `character varying(20)` | 허용 | — |
| `is_pinned` | `boolean` | 불가 | — |
| `published_at` | `timestamp with time zone` | 허용 | — |
| `publish_start_at` | `timestamp with time zone` | 허용 | — |
| `publish_end_at` | `timestamp with time zone` | 허용 | — |
| `closed_at` | `timestamp with time zone` | 허용 | — |
| `view_count` | `integer` | 불가 | — |
| `author_user_id` | `bigint` | 불가 | — |
| `author_username` | `character varying(50)` | 불가 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_notices_priority`: `CHECK (priority::text = ANY (ARRAY['normal'::character varying, 'important'::character varying, 'urgent'::character varying]::text[]))`
- CHECK `ck_notices_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'published'::character varying, 'closed'::character varying]::text[]))`
- CHECK `ck_notices_target_role`: `CHECK (target_role IS NULL OR (target_role::text = ANY (ARRAY['admin'::character varying, 'employee'::character varying]::text[])))`
- CHECK `ck_notices_view_count`: `CHECK (view_count >= 0)`
- CHECK `ck_notices_visibility`: `CHECK (visibility_type::text = ANY (ARRAY['all'::character varying, 'store'::character varying, 'role'::character varying]::text[]))`
- FK `notices_author_user_id_fkey`: `FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- FK `notices_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `notices_target_store_id_fkey`: `FOREIGN KEY (target_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `notices_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_notices_is_deleted`: `CREATE INDEX ix_notices_is_deleted ON public.notices USING btree (is_deleted)`
- `ix_notices_is_pinned`: `CREATE INDEX ix_notices_is_pinned ON public.notices USING btree (is_pinned)`
- `ix_notices_priority`: `CREATE INDEX ix_notices_priority ON public.notices USING btree (priority)`
- `ix_notices_publish_end_at`: `CREATE INDEX ix_notices_publish_end_at ON public.notices USING btree (publish_end_at)`
- `ix_notices_publish_start_at`: `CREATE INDEX ix_notices_publish_start_at ON public.notices USING btree (publish_start_at)`
- `ix_notices_published_at`: `CREATE INDEX ix_notices_published_at ON public.notices USING btree (published_at)`
- `ix_notices_status`: `CREATE INDEX ix_notices_status ON public.notices USING btree (status)`
- `ix_notices_target_store_id`: `CREATE INDEX ix_notices_target_store_id ON public.notices USING btree (target_store_id)`
- `ix_notices_title`: `CREATE INDEX ix_notices_title ON public.notices USING btree (title)`
- `ix_notices_visibility_type`: `CREATE INDEX ix_notices_visibility_type ON public.notices USING btree (visibility_type)`
- `notices_pkey`: `CREATE UNIQUE INDEX notices_pkey ON public.notices USING btree (id)`

### `products`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('products_id_seq'::regclass)` |
| `product_code` | `character varying(50)` | 불가 | — |
| `name` | `character varying(200)` | 불가 | — |
| `model_name` | `character varying(150)` | 허용 | — |
| `category` | `character varying(100)` | 허용 | — |
| `brand` | `character varying(100)` | 허용 | — |
| `option_name` | `character varying(200)` | 허용 | — |
| `barcode` | `character varying(100)` | 허용 | — |
| `sale_price` | `numeric(14,2)` | 허용 | — |
| `cost_price` | `numeric(14,2)` | 허용 | — |
| `status` | `character varying(20)` | 불가 | — |
| `serial_managed` | `boolean` | 불가 | — |
| `warranty_months` | `integer` | 불가 | — |
| `memo` | `text` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |
| `safety_stock` | `integer` | 불가 | `0` |

**제약조건**

- CHECK `ck_products_cost_price_nonnegative`: `CHECK (cost_price IS NULL OR cost_price >= 0::numeric)`
- CHECK `ck_products_safety_stock_nonnegative`: `CHECK (safety_stock >= 0)`
- CHECK `ck_products_sale_price_nonnegative`: `CHECK (sale_price IS NULL OR sale_price >= 0::numeric)`
- CHECK `ck_products_status`: `CHECK (status::text = ANY (ARRAY['active'::character varying, 'inactive'::character varying]::text[]))`
- CHECK `ck_products_warranty_nonnegative`: `CHECK (warranty_months >= 0)`
- PK `products_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_products_barcode`: `UNIQUE (barcode)`

**인덱스**

- `ix_products_barcode`: `CREATE INDEX ix_products_barcode ON public.products USING btree (barcode)`
- `ix_products_category`: `CREATE INDEX ix_products_category ON public.products USING btree (category)`
- `ix_products_model_name`: `CREATE INDEX ix_products_model_name ON public.products USING btree (model_name)`
- `ix_products_name`: `CREATE INDEX ix_products_name ON public.products USING btree (name)`
- `ix_products_product_code`: `CREATE UNIQUE INDEX ix_products_product_code ON public.products USING btree (product_code)`
- `ix_products_status`: `CREATE INDEX ix_products_status ON public.products USING btree (status)`
- `products_pkey`: `CREATE UNIQUE INDEX products_pkey ON public.products USING btree (id)`
- `uq_products_barcode`: `CREATE UNIQUE INDEX uq_products_barcode ON public.products USING btree (barcode)`

### `purchase_order_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('purchase_order_items_id_seq'::regclass)` |
| `purchase_order_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `product_code_snapshot` | `character varying(50)` | 불가 | — |
| `product_name_snapshot` | `character varying(200)` | 불가 | — |
| `model_name_snapshot` | `character varying(150)` | 허용 | — |
| `ordered_quantity` | `integer` | 불가 | — |
| `received_quantity` | `integer` | 불가 | — |
| `unit_cost` | `numeric(14,2)` | 불가 | — |
| `line_amount` | `numeric(14,2)` | 불가 | — |
| `memo` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_po_items_amount`: `CHECK (unit_cost >= 0::numeric AND line_amount >= 0::numeric)`
- CHECK `ck_po_items_quantity`: `CHECK (ordered_quantity >= 1 AND received_quantity >= 0 AND received_quantity <= ordered_quantity)`
- FK `purchase_order_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `purchase_order_items_purchase_order_id_fkey`: `FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE`
- PK `purchase_order_items_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_po_items_order`: `CREATE INDEX ix_po_items_order ON public.purchase_order_items USING btree (purchase_order_id)`
- `ix_po_items_product`: `CREATE INDEX ix_po_items_product ON public.purchase_order_items USING btree (product_id)`
- `purchase_order_items_pkey`: `CREATE UNIQUE INDEX purchase_order_items_pkey ON public.purchase_order_items USING btree (id)`

### `purchase_order_status_histories`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('purchase_order_status_histories_id_seq'::regclass)` |
| `purchase_order_id` | `bigint` | 불가 | — |
| `previous_status` | `character varying(30)` | 허용 | — |
| `new_status` | `character varying(30)` | 불가 | — |
| `changed_by_user_id` | `bigint` | 허용 | — |
| `changed_by_username` | `character varying(50)` | 불가 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `changed_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `purchase_order_status_histories_changed_by_user_id_fkey`: `FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `purchase_order_status_histories_purchase_order_id_fkey`: `FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE`
- PK `purchase_order_status_histories_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_purchase_order_status_histories_purchase_order_id`: `CREATE INDEX ix_purchase_order_status_histories_purchase_order_id ON public.purchase_order_status_histories USING btree (purchase_order_id)`
- `purchase_order_status_histories_pkey`: `CREATE UNIQUE INDEX purchase_order_status_histories_pkey ON public.purchase_order_status_histories USING btree (id)`

### `purchase_orders`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('purchase_orders_id_seq'::regclass)` |
| `purchase_order_code` | `character varying(30)` | 불가 | — |
| `requesting_store_id` | `bigint` | 불가 | — |
| `requested_by_employee_id` | `bigint` | 허용 | — |
| `supplier_name` | `character varying(150)` | 허용 | — |
| `marketplace_id` | `bigint` | 허용 | — |
| `status` | `character varying(30)` | 불가 | — |
| `requested_at` | `timestamp with time zone` | 허용 | — |
| `approved_at` | `timestamp with time zone` | 허용 | — |
| `approved_by_user_id` | `bigint` | 허용 | — |
| `expected_receipt_date` | `date` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `cancellation_reason` | `character varying(500)` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `is_deleted` | `boolean` | 불가 | — |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_purchase_orders_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'requested'::character varying, 'approved'::character varying, 'partially_received'::character varying, 'received'::character varying, 'cancelled'::character varying]::text[]))`
- FK `purchase_orders_approved_by_user_id_fkey`: `FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `purchase_orders_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `purchase_orders_marketplace_id_fkey`: `FOREIGN KEY (marketplace_id) REFERENCES marketplaces(id) ON DELETE SET NULL`
- FK `purchase_orders_requested_by_employee_id_fkey`: `FOREIGN KEY (requested_by_employee_id) REFERENCES employees(id) ON DELETE SET NULL`
- FK `purchase_orders_requesting_store_id_fkey`: `FOREIGN KEY (requesting_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `purchase_orders_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_purchase_orders_code`: `CREATE UNIQUE INDEX ix_purchase_orders_code ON public.purchase_orders USING btree (purchase_order_code)`
- `ix_purchase_orders_requested_at`: `CREATE INDEX ix_purchase_orders_requested_at ON public.purchase_orders USING btree (requested_at)`
- `ix_purchase_orders_status`: `CREATE INDEX ix_purchase_orders_status ON public.purchase_orders USING btree (status)`
- `ix_purchase_orders_store`: `CREATE INDEX ix_purchase_orders_store ON public.purchase_orders USING btree (requesting_store_id)`
- `purchase_orders_pkey`: `CREATE UNIQUE INDEX purchase_orders_pkey ON public.purchase_orders USING btree (id)`

### `sale_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sale_items_id_seq'::regclass)` |
| `sale_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `product_code_snapshot` | `character varying(50)` | 불가 | — |
| `product_name_snapshot` | `character varying(200)` | 불가 | — |
| `model_name_snapshot` | `character varying(150)` | 허용 | — |
| `quantity` | `integer` | 불가 | — |
| `unit_price` | `numeric(14,2)` | 불가 | — |
| `item_discount_amount` | `numeric(14,2)` | 불가 | `'0'::numeric` |
| `line_amount` | `numeric(14,2)` | 불가 | — |
| `serial_number` | `character varying(100)` | 허용 | — |
| `memo` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_sale_items_amounts`: `CHECK (unit_price >= 0::numeric AND item_discount_amount >= 0::numeric AND line_amount >= 0::numeric)`
- CHECK `ck_sale_items_quantity`: `CHECK (quantity >= 1)`
- FK `sale_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `sale_items_sale_id_fkey`: `FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE`
- PK `sale_items_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sale_items_product_id`: `CREATE INDEX ix_sale_items_product_id ON public.sale_items USING btree (product_id)`
- `ix_sale_items_sale_id`: `CREATE INDEX ix_sale_items_sale_id ON public.sale_items USING btree (sale_id)`
- `ix_sale_items_serial_number`: `CREATE INDEX ix_sale_items_serial_number ON public.sale_items USING btree (serial_number)`
- `sale_items_pkey`: `CREATE UNIQUE INDEX sale_items_pkey ON public.sale_items USING btree (id)`

### `sale_payments`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sale_payments_id_seq'::regclass)` |
| `sale_id` | `bigint` | 불가 | — |
| `payment_method` | `character varying(30)` | 불가 | — |
| `amount` | `numeric(14,2)` | 불가 | — |
| `paid_at` | `timestamp with time zone` | 불가 | — |
| `reference_number` | `character varying(100)` | 허용 | — |
| `card_company` | `character varying(50)` | 허용 | — |
| `installment_months` | `integer` | 불가 | `0` |
| `memo` | `character varying(500)` | 허용 | — |
| `is_cancelled` | `boolean` | 불가 | `false` |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_sale_payments_amount_positive`: `CHECK (amount > 0::numeric)`
- CHECK `ck_sale_payments_installments`: `CHECK (installment_months >= 0)`
- FK `sale_payments_sale_id_fkey`: `FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE`
- PK `sale_payments_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sale_payments_cancelled`: `CREATE INDEX ix_sale_payments_cancelled ON public.sale_payments USING btree (is_cancelled)`
- `ix_sale_payments_paid_at`: `CREATE INDEX ix_sale_payments_paid_at ON public.sale_payments USING btree (paid_at)`
- `ix_sale_payments_payment_method`: `CREATE INDEX ix_sale_payments_payment_method ON public.sale_payments USING btree (payment_method)`
- `ix_sale_payments_sale_id`: `CREATE INDEX ix_sale_payments_sale_id ON public.sale_payments USING btree (sale_id)`
- `sale_payments_pkey`: `CREATE UNIQUE INDEX sale_payments_pkey ON public.sale_payments USING btree (id)`

### `sale_status_histories`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sale_status_histories_id_seq'::regclass)` |
| `sale_id` | `bigint` | 불가 | — |
| `previous_status` | `character varying(30)` | 허용 | — |
| `new_status` | `character varying(30)` | 불가 | — |
| `changed_by_user_id` | `bigint` | 허용 | — |
| `changed_by_username` | `character varying(100)` | 허용 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `changed_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `sale_status_histories_changed_by_user_id_fkey`: `FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `sale_status_histories_sale_id_fkey`: `FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE`
- PK `sale_status_histories_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sale_status_histories_changed_at`: `CREATE INDEX ix_sale_status_histories_changed_at ON public.sale_status_histories USING btree (changed_at)`
- `ix_sale_status_histories_new_status`: `CREATE INDEX ix_sale_status_histories_new_status ON public.sale_status_histories USING btree (new_status)`
- `ix_sale_status_histories_sale_id`: `CREATE INDEX ix_sale_status_histories_sale_id ON public.sale_status_histories USING btree (sale_id)`
- `sale_status_histories_pkey`: `CREATE UNIQUE INDEX sale_status_histories_pkey ON public.sale_status_histories USING btree (id)`

### `sales`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sales_id_seq'::regclass)` |
| `sale_code` | `character varying(30)` | 불가 | — |
| `customer_id` | `bigint` | 불가 | — |
| `store_id` | `bigint` | 불가 | — |
| `employee_id` | `bigint` | 불가 | — |
| `marketplace_id` | `bigint` | 허용 | — |
| `sale_type` | `character varying(30)` | 불가 | `'normal'::character varying` |
| `status` | `character varying(30)` | 불가 | `'confirmed'::character varying` |
| `sold_at` | `timestamp with time zone` | 불가 | — |
| `subtotal_amount` | `numeric(14,2)` | 불가 | — |
| `discount_amount` | `numeric(14,2)` | 불가 | `'0'::numeric` |
| `final_amount` | `numeric(14,2)` | 불가 | — |
| `paid_amount` | `numeric(14,2)` | 불가 | `'0'::numeric` |
| `payment_status` | `character varying(20)` | 불가 | `'unpaid'::character varying` |
| `cancellation_reason` | `character varying(500)` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `is_deleted` | `boolean` | 불가 | `false` |
| `deleted_at` | `timestamp with time zone` | 허용 | — |
| `deleted_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_sales_amounts_nonnegative`: `CHECK (subtotal_amount >= 0::numeric AND discount_amount >= 0::numeric AND final_amount >= 0::numeric AND paid_amount >= 0::numeric)`
- CHECK `ck_sales_payment_status`: `CHECK (payment_status::text = ANY (ARRAY['unpaid'::character varying, 'partial'::character varying, 'paid'::character varying, 'refunded'::character varying]::text[]))`
- CHECK `ck_sales_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'confirmed'::character varying, 'payment_completed'::character varying, 'cancelled'::character varying]::text[]))`
- FK `sales_customer_id_fkey`: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT`
- FK `sales_deleted_by_fkey`: `FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `sales_employee_id_fkey`: `FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT`
- FK `sales_marketplace_id_fkey`: `FOREIGN KEY (marketplace_id) REFERENCES marketplaces(id) ON DELETE RESTRICT`
- FK `sales_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- PK `sales_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sales_created_at`: `CREATE INDEX ix_sales_created_at ON public.sales USING btree (created_at)`
- `ix_sales_customer_id`: `CREATE INDEX ix_sales_customer_id ON public.sales USING btree (customer_id)`
- `ix_sales_employee_id`: `CREATE INDEX ix_sales_employee_id ON public.sales USING btree (employee_id)`
- `ix_sales_is_deleted`: `CREATE INDEX ix_sales_is_deleted ON public.sales USING btree (is_deleted)`
- `ix_sales_marketplace_id`: `CREATE INDEX ix_sales_marketplace_id ON public.sales USING btree (marketplace_id)`
- `ix_sales_payment_status`: `CREATE INDEX ix_sales_payment_status ON public.sales USING btree (payment_status)`
- `ix_sales_sale_code`: `CREATE UNIQUE INDEX ix_sales_sale_code ON public.sales USING btree (sale_code)`
- `ix_sales_sold_at`: `CREATE INDEX ix_sales_sold_at ON public.sales USING btree (sold_at)`
- `ix_sales_status`: `CREATE INDEX ix_sales_status ON public.sales USING btree (status)`
- `ix_sales_store_id`: `CREATE INDEX ix_sales_store_id ON public.sales USING btree (store_id)`
- `sales_pkey`: `CREATE UNIQUE INDEX sales_pkey ON public.sales USING btree (id)`

### `serial_bulk_update_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('serial_bulk_update_items_id_seq'::regclass)` |
| `job_id` | `bigint` | 불가 | — |
| `source_serial_number` | `character varying(150)` | 불가 | — |
| `normalized_source_serial` | `character varying(150)` | 불가 | — |
| `target_serial_number` | `character varying(150)` | 불가 | — |
| `normalized_target_serial` | `character varying(150)` | 불가 | — |
| `product_id` | `bigint` | 허용 | — |
| `current_store_id` | `bigint` | 허용 | — |
| `current_status` | `character varying(30)` | 허용 | — |
| `validation_status` | `character varying(20)` | 불가 | — |
| `validation_message` | `character varying(500)` | 허용 | — |
| `apply_status` | `character varying(20)` | 불가 | — |
| `error_message` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_serial_item_apply`: `CHECK (apply_status::text = ANY (ARRAY['pending'::character varying, 'applied'::character varying, 'failed'::character varying]::text[]))`
- CHECK `ck_serial_item_validation`: `CHECK (validation_status::text = ANY (ARRAY['pending'::character varying, 'valid'::character varying, 'invalid'::character varying]::text[]))`
- FK `serial_bulk_update_items_current_store_id_fkey`: `FOREIGN KEY (current_store_id) REFERENCES stores(id) ON DELETE SET NULL`
- FK `serial_bulk_update_items_job_id_fkey`: `FOREIGN KEY (job_id) REFERENCES serial_bulk_update_jobs(id) ON DELETE CASCADE`
- FK `serial_bulk_update_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL`
- PK `serial_bulk_update_items_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_serial_item_apply`: `CREATE INDEX ix_serial_item_apply ON public.serial_bulk_update_items USING btree (apply_status)`
- `ix_serial_item_job`: `CREATE INDEX ix_serial_item_job ON public.serial_bulk_update_items USING btree (job_id)`
- `ix_serial_item_source`: `CREATE INDEX ix_serial_item_source ON public.serial_bulk_update_items USING btree (normalized_source_serial)`
- `ix_serial_item_target`: `CREATE INDEX ix_serial_item_target ON public.serial_bulk_update_items USING btree (normalized_target_serial)`
- `ix_serial_item_validation`: `CREATE INDEX ix_serial_item_validation ON public.serial_bulk_update_items USING btree (validation_status)`
- `serial_bulk_update_items_pkey`: `CREATE UNIQUE INDEX serial_bulk_update_items_pkey ON public.serial_bulk_update_items USING btree (id)`

### `serial_bulk_update_jobs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('serial_bulk_update_jobs_id_seq'::regclass)` |
| `job_code` | `character varying(30)` | 불가 | — |
| `status` | `character varying(30)` | 불가 | — |
| `total_count` | `integer` | 불가 | — |
| `valid_count` | `integer` | 불가 | — |
| `invalid_count` | `integer` | 불가 | — |
| `applied_count` | `integer` | 불가 | — |
| `failed_count` | `integer` | 불가 | — |
| `reason` | `character varying(500)` | 불가 | — |
| `requested_by_user_id` | `bigint` | 불가 | — |
| `approved_by_user_id` | `bigint` | 허용 | — |
| `validated_at` | `timestamp with time zone` | 허용 | — |
| `approved_at` | `timestamp with time zone` | 허용 | — |
| `applied_at` | `timestamp with time zone` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_serial_bulk_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'validated'::character varying, 'approved'::character varying, 'applied'::character varying, 'partially_failed'::character varying, 'failed'::character varying, 'cancelled'::character varying]::text[]))`
- FK `serial_bulk_update_jobs_approved_by_user_id_fkey`: `FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `serial_bulk_update_jobs_requested_by_user_id_fkey`: `FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- PK `serial_bulk_update_jobs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_serial_bulk_code`: `CREATE UNIQUE INDEX ix_serial_bulk_code ON public.serial_bulk_update_jobs USING btree (job_code)`
- `ix_serial_bulk_created`: `CREATE INDEX ix_serial_bulk_created ON public.serial_bulk_update_jobs USING btree (created_at)`
- `ix_serial_bulk_status`: `CREATE INDEX ix_serial_bulk_status ON public.serial_bulk_update_jobs USING btree (status)`
- `serial_bulk_update_jobs_pkey`: `CREATE UNIQUE INDEX serial_bulk_update_jobs_pkey ON public.serial_bulk_update_jobs USING btree (id)`

### `serial_inventories`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('serial_inventories_id_seq'::regclass)` |
| `serial_number` | `character varying(150)` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `store_id` | `bigint` | 허용 | — |
| `status` | `character varying(30)` | 불가 | — |
| `source_receipt_item_id` | `bigint` | 허용 | — |
| `current_logistics_item_id` | `bigint` | 허용 | — |
| `last_movement_id` | `bigint` | 허용 | — |
| `received_at` | `timestamp with time zone` | 허용 | — |
| `shipped_at` | `timestamp with time zone` | 허용 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_serial_status`: `CHECK (status::text = ANY (ARRAY['in_stock'::character varying, 'reserved'::character varying, 'in_transfer'::character varying, 'shipped'::character varying, 'customer_owned'::character varying, 'as_in_service'::character varying, 'returned'::character varying, 'cancelled'::character varying]::text[]))`
- FK `serial_inventories_current_logistics_item_id_fkey`: `FOREIGN KEY (current_logistics_item_id) REFERENCES logistics_items(id) ON DELETE SET NULL`
- FK `serial_inventories_last_movement_id_fkey`: `FOREIGN KEY (last_movement_id) REFERENCES inventory_movements(id) ON DELETE SET NULL`
- FK `serial_inventories_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `serial_inventories_source_receipt_item_id_fkey`: `FOREIGN KEY (source_receipt_item_id) REFERENCES goods_receipt_items(id) ON DELETE SET NULL`
- FK `serial_inventories_store_id_fkey`: `FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL`
- PK `serial_inventories_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_serial_number`: `CREATE UNIQUE INDEX ix_serial_number ON public.serial_inventories USING btree (serial_number)`
- `ix_serial_product`: `CREATE INDEX ix_serial_product ON public.serial_inventories USING btree (product_id)`
- `ix_serial_status`: `CREATE INDEX ix_serial_status ON public.serial_inventories USING btree (status)`
- `ix_serial_store`: `CREATE INDEX ix_serial_store ON public.serial_inventories USING btree (store_id)`
- `serial_inventories_pkey`: `CREATE UNIQUE INDEX serial_inventories_pkey ON public.serial_inventories USING btree (id)`

### `serial_number_corrections`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('serial_number_corrections_id_seq'::regclass)` |
| `bulk_update_job_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `old_serial_number` | `character varying(150)` | 불가 | — |
| `new_serial_number` | `character varying(150)` | 불가 | — |
| `reason` | `character varying(500)` | 불가 | — |
| `corrected_by_user_id` | `bigint` | 불가 | — |
| `corrected_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `serial_number_corrections_bulk_update_job_id_fkey`: `FOREIGN KEY (bulk_update_job_id) REFERENCES serial_bulk_update_jobs(id) ON DELETE RESTRICT`
- FK `serial_number_corrections_corrected_by_user_id_fkey`: `FOREIGN KEY (corrected_by_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- FK `serial_number_corrections_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- PK `serial_number_corrections_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_serial_correction_at`: `CREATE INDEX ix_serial_correction_at ON public.serial_number_corrections USING btree (corrected_at)`
- `ix_serial_correction_new`: `CREATE INDEX ix_serial_correction_new ON public.serial_number_corrections USING btree (new_serial_number)`
- `ix_serial_correction_old`: `CREATE INDEX ix_serial_correction_old ON public.serial_number_corrections USING btree (old_serial_number)`
- `ix_serial_correction_product`: `CREATE INDEX ix_serial_correction_product ON public.serial_number_corrections USING btree (product_id)`
- `serial_number_corrections_pkey`: `CREATE UNIQUE INDEX serial_number_corrections_pkey ON public.serial_number_corrections USING btree (id)`

### `shipments`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('shipments_id_seq'::regclass)` |
| `logistics_order_id` | `bigint` | 불가 | — |
| `carrier_code` | `character varying(30)` | 허용 | — |
| `carrier_name` | `character varying(100)` | 허용 | — |
| `tracking_number` | `character varying(100)` | 불가 | — |
| `shipment_status` | `character varying(20)` | 불가 | `'registered'::character varying` |
| `shipped_at` | `timestamp with time zone` | 허용 | — |
| `delivered_at` | `timestamp with time zone` | 허용 | — |
| `tracking_url` | `character varying(500)` | 허용 | — |
| `memo` | `character varying(500)` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_shipments_status`: `CHECK (shipment_status::text = ANY (ARRAY['pending'::character varying, 'registered'::character varying, 'in_transit'::character varying, 'delivered'::character varying, 'cancelled'::character varying]::text[]))`
- FK `shipments_logistics_order_id_fkey`: `FOREIGN KEY (logistics_order_id) REFERENCES logistics_orders(id) ON DELETE CASCADE`
- PK `shipments_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_shipments_order_tracking`: `UNIQUE (logistics_order_id, tracking_number)`

**인덱스**

- `ix_shipments_carrier`: `CREATE INDEX ix_shipments_carrier ON public.shipments USING btree (carrier_code)`
- `ix_shipments_delivered_at`: `CREATE INDEX ix_shipments_delivered_at ON public.shipments USING btree (delivered_at)`
- `ix_shipments_order_id`: `CREATE INDEX ix_shipments_order_id ON public.shipments USING btree (logistics_order_id)`
- `ix_shipments_shipped_at`: `CREATE INDEX ix_shipments_shipped_at ON public.shipments USING btree (shipped_at)`
- `ix_shipments_status`: `CREATE INDEX ix_shipments_status ON public.shipments USING btree (shipment_status)`
- `ix_shipments_tracking`: `CREATE INDEX ix_shipments_tracking ON public.shipments USING btree (tracking_number)`
- `shipments_pkey`: `CREATE UNIQUE INDEX shipments_pkey ON public.shipments USING btree (id)`
- `uq_shipments_order_tracking`: `CREATE UNIQUE INDEX uq_shipments_order_tracking ON public.shipments USING btree (logistics_order_id, tracking_number)`

### `sms_opt_outs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sms_opt_outs_id_seq'::regclass)` |
| `customer_id` | `bigint` | 허용 | — |
| `normalized_phone_hash` | `character varying(64)` | 불가 | — |
| `phone_last4` | `character varying(4)` | 허용 | — |
| `opt_out_type` | `character varying(20)` | 불가 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `opted_out_at` | `timestamp with time zone` | 불가 | — |
| `opted_out_by_user_id` | `bigint` | 허용 | — |
| `is_active` | `boolean` | 불가 | — |
| `revoked_at` | `timestamp with time zone` | 허용 | — |
| `revoked_by_user_id` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_sms_opt_out_type`: `CHECK (opt_out_type::text = ANY (ARRAY['marketing'::character varying, 'all'::character varying]::text[]))`
- FK `sms_opt_outs_customer_id_fkey`: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL`
- FK `sms_opt_outs_opted_out_by_user_id_fkey`: `FOREIGN KEY (opted_out_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `sms_opt_outs_revoked_by_user_id_fkey`: `FOREIGN KEY (revoked_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- PK `sms_opt_outs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sms_opt_out_active`: `CREATE INDEX ix_sms_opt_out_active ON public.sms_opt_outs USING btree (is_active)`
- `ix_sms_opt_out_customer`: `CREATE INDEX ix_sms_opt_out_customer ON public.sms_opt_outs USING btree (customer_id)`
- `ix_sms_opt_out_hash`: `CREATE INDEX ix_sms_opt_out_hash ON public.sms_opt_outs USING btree (normalized_phone_hash)`
- `sms_opt_outs_pkey`: `CREATE UNIQUE INDEX sms_opt_outs_pkey ON public.sms_opt_outs USING btree (id)`

### `sms_send_logs`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sms_send_logs_id_seq'::regclass)` |
| `sms_send_code` | `character varying(30)` | 불가 | — |
| `template_id` | `bigint` | 허용 | — |
| `customer_id` | `bigint` | 허용 | — |
| `recipient_phone_hash` | `character varying(64)` | 불가 | — |
| `recipient_phone_last4` | `character varying(4)` | 허용 | — |
| `message_type` | `character varying(30)` | 불가 | — |
| `category` | `character varying(30)` | 불가 | — |
| `rendered_subject` | `character varying(200)` | 허용 | — |
| `rendered_content` | `text` | 허용 | — |
| `status` | `character varying(20)` | 불가 | — |
| `provider` | `character varying(30)` | 불가 | — |
| `provider_message_id` | `character varying(100)` | 허용 | — |
| `error_code` | `character varying(50)` | 허용 | — |
| `error_message` | `character varying(500)` | 허용 | — |
| `requested_at` | `timestamp with time zone` | 불가 | — |
| `sent_at` | `timestamp with time zone` | 허용 | — |
| `created_by` | `bigint` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_sms_send_status`: `CHECK (status::text = ANY (ARRAY['draft'::character varying, 'queued'::character varying, 'blocked'::character varying, 'dry_run'::character varying, 'sent'::character varying, 'failed'::character varying, 'cancelled'::character varying]::text[]))`
- FK `sms_send_logs_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `sms_send_logs_customer_id_fkey`: `FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL`
- FK `sms_send_logs_template_id_fkey`: `FOREIGN KEY (template_id) REFERENCES sms_templates(id) ON DELETE SET NULL`
- PK `sms_send_logs_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sms_send_code`: `CREATE UNIQUE INDEX ix_sms_send_code ON public.sms_send_logs USING btree (sms_send_code)`
- `ix_sms_send_customer`: `CREATE INDEX ix_sms_send_customer ON public.sms_send_logs USING btree (customer_id)`
- `ix_sms_send_requested`: `CREATE INDEX ix_sms_send_requested ON public.sms_send_logs USING btree (requested_at)`
- `ix_sms_send_status`: `CREATE INDEX ix_sms_send_status ON public.sms_send_logs USING btree (status)`
- `sms_send_logs_pkey`: `CREATE UNIQUE INDEX sms_send_logs_pkey ON public.sms_send_logs USING btree (id)`

### `sms_templates`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('sms_templates_id_seq'::regclass)` |
| `template_code` | `character varying(50)` | 불가 | — |
| `template_name` | `character varying(150)` | 불가 | — |
| `message_type` | `character varying(30)` | 불가 | — |
| `category` | `character varying(30)` | 불가 | — |
| `subject` | `character varying(200)` | 허용 | — |
| `content` | `text` | 불가 | — |
| `allowed_variables` | `json` | 불가 | — |
| `is_active` | `boolean` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_sms_template_type`: `CHECK (message_type::text = ANY (ARRAY['sms'::character varying, 'lms'::character varying, 'alimtalk_placeholder'::character varying]::text[]))`
- FK `sms_templates_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL`
- FK `sms_templates_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `sms_templates_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_sms_template_active`: `CREATE INDEX ix_sms_template_active ON public.sms_templates USING btree (is_active)`
- `ix_sms_template_category`: `CREATE INDEX ix_sms_template_category ON public.sms_templates USING btree (category)`
- `ix_sms_template_code`: `CREATE UNIQUE INDEX ix_sms_template_code ON public.sms_templates USING btree (template_code)`
- `sms_templates_pkey`: `CREATE UNIQUE INDEX sms_templates_pkey ON public.sms_templates USING btree (id)`

### `stock_transfer_items`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('stock_transfer_items_id_seq'::regclass)` |
| `stock_transfer_id` | `bigint` | 불가 | — |
| `product_id` | `bigint` | 불가 | — |
| `quantity` | `integer` | 불가 | — |
| `serial_number` | `character varying(150)` | 허용 | — |
| `product_code_snapshot` | `character varying(50)` | 불가 | — |
| `product_name_snapshot` | `character varying(200)` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_transfer_items_quantity`: `CHECK (quantity >= 1)`
- FK `stock_transfer_items_product_id_fkey`: `FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT`
- FK `stock_transfer_items_stock_transfer_id_fkey`: `FOREIGN KEY (stock_transfer_id) REFERENCES stock_transfers(id) ON DELETE CASCADE`
- PK `stock_transfer_items_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_transfer_serial`: `UNIQUE (stock_transfer_id, serial_number)`

**인덱스**

- `stock_transfer_items_pkey`: `CREATE UNIQUE INDEX stock_transfer_items_pkey ON public.stock_transfer_items USING btree (id)`
- `uq_transfer_serial`: `CREATE UNIQUE INDEX uq_transfer_serial ON public.stock_transfer_items USING btree (stock_transfer_id, serial_number)`

### `stock_transfer_status_histories`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('stock_transfer_status_histories_id_seq'::regclass)` |
| `stock_transfer_id` | `bigint` | 불가 | — |
| `previous_status` | `character varying(20)` | 허용 | — |
| `new_status` | `character varying(20)` | 불가 | — |
| `changed_by_user_id` | `bigint` | 허용 | — |
| `changed_by_username` | `character varying(50)` | 불가 | — |
| `reason` | `character varying(500)` | 허용 | — |
| `changed_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- FK `stock_transfer_status_histories_changed_by_user_id_fkey`: `FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `stock_transfer_status_histories_stock_transfer_id_fkey`: `FOREIGN KEY (stock_transfer_id) REFERENCES stock_transfers(id) ON DELETE CASCADE`
- PK `stock_transfer_status_histories_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_stock_transfer_status_histories_stock_transfer_id`: `CREATE INDEX ix_stock_transfer_status_histories_stock_transfer_id ON public.stock_transfer_status_histories USING btree (stock_transfer_id)`
- `stock_transfer_status_histories_pkey`: `CREATE UNIQUE INDEX stock_transfer_status_histories_pkey ON public.stock_transfer_status_histories USING btree (id)`

### `stock_transfers`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('stock_transfers_id_seq'::regclass)` |
| `stock_transfer_code` | `character varying(30)` | 불가 | — |
| `origin_store_id` | `bigint` | 불가 | — |
| `destination_store_id` | `bigint` | 불가 | — |
| `requested_by_user_id` | `bigint` | 불가 | — |
| `approved_by_user_id` | `bigint` | 허용 | — |
| `status` | `character varying(20)` | 불가 | — |
| `requested_at` | `timestamp with time zone` | 불가 | — |
| `approved_at` | `timestamp with time zone` | 허용 | — |
| `shipped_at` | `timestamp with time zone` | 허용 | — |
| `received_at` | `timestamp with time zone` | 허용 | — |
| `cancelled_at` | `timestamp with time zone` | 허용 | — |
| `cancellation_reason` | `character varying(500)` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |

**제약조건**

- CHECK `ck_transfer_status`: `CHECK (status::text = ANY (ARRAY['requested'::character varying, 'approved'::character varying, 'in_transit'::character varying, 'received'::character varying, 'cancelled'::character varying]::text[]))`
- FK `stock_transfers_approved_by_user_id_fkey`: `FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL`
- FK `stock_transfers_destination_store_id_fkey`: `FOREIGN KEY (destination_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- FK `stock_transfers_origin_store_id_fkey`: `FOREIGN KEY (origin_store_id) REFERENCES stores(id) ON DELETE RESTRICT`
- FK `stock_transfers_requested_by_user_id_fkey`: `FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- PK `stock_transfers_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_transfer_code`: `CREATE UNIQUE INDEX ix_transfer_code ON public.stock_transfers USING btree (stock_transfer_code)`
- `ix_transfer_destination`: `CREATE INDEX ix_transfer_destination ON public.stock_transfers USING btree (destination_store_id)`
- `ix_transfer_origin`: `CREATE INDEX ix_transfer_origin ON public.stock_transfers USING btree (origin_store_id)`
- `ix_transfer_status`: `CREATE INDEX ix_transfer_status ON public.stock_transfers USING btree (status)`
- `stock_transfers_pkey`: `CREATE UNIQUE INDEX stock_transfers_pkey ON public.stock_transfers USING btree (id)`

### `stores`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('stores_id_seq'::regclass)` |
| `code` | `character varying(30)` | 불가 | — |
| `name` | `character varying(150)` | 불가 | — |
| `store_type` | `character varying(50)` | 허용 | — |
| `department_store` | `character varying(150)` | 허용 | — |
| `address` | `character varying(500)` | 허용 | — |
| `phone` | `character varying(30)` | 허용 | — |
| `manager_name` | `character varying(100)` | 허용 | — |
| `status` | `character varying(20)` | 불가 | — |
| `opened_at` | `date` | 허용 | — |
| `closed_at` | `date` | 허용 | — |
| `memo` | `text` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_stores_status`: `CHECK (status::text = ANY (ARRAY['active'::character varying, 'inactive'::character varying]::text[]))`
- PK `stores_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_stores_code`: `CREATE UNIQUE INDEX ix_stores_code ON public.stores USING btree (code)`
- `ix_stores_name`: `CREATE INDEX ix_stores_name ON public.stores USING btree (name)`
- `ix_stores_status`: `CREATE INDEX ix_stores_status ON public.stores USING btree (status)`
- `ix_stores_store_type`: `CREATE INDEX ix_stores_store_type ON public.stores USING btree (store_type)`
- `stores_pkey`: `CREATE UNIQUE INDEX stores_pkey ON public.stores USING btree (id)`

### `system_settings`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('system_settings_id_seq'::regclass)` |
| `setting_key` | `character varying(100)` | 불가 | — |
| `setting_name` | `character varying(150)` | 불가 | — |
| `category` | `character varying(30)` | 불가 | — |
| `value_type` | `character varying(20)` | 불가 | — |
| `setting_value` | `text` | 허용 | — |
| `default_value` | `text` | 허용 | — |
| `description` | `character varying(500)` | 허용 | — |
| `is_secret` | `boolean` | 불가 | — |
| `is_editable` | `boolean` | 불가 | — |
| `validation_rule` | `json` | 허용 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_system_settings_category`: `CHECK (category::text = ANY (ARRAY['general'::character varying, 'customer'::character varying, 'sales'::character varying, 'logistics'::character varying, 'inventory'::character varying, 'as'::character varying, 'sms'::character varying, 'batch'::character varying, 'security'::character varying, 'ai'::character varying]::text[]))`
- CHECK `ck_system_settings_type`: `CHECK (value_type::text = ANY (ARRAY['string'::character varying, 'integer'::character varying, 'boolean'::character varying, 'decimal'::character varying, 'json'::character varying]::text[]))`
- FK `system_settings_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL`
- PK `system_settings_pkey`: `PRIMARY KEY (id)`

**인덱스**

- `ix_system_settings_category`: `CREATE INDEX ix_system_settings_category ON public.system_settings USING btree (category)`
- `ix_system_settings_editable`: `CREATE INDEX ix_system_settings_editable ON public.system_settings USING btree (is_editable)`
- `ix_system_settings_key`: `CREATE UNIQUE INDEX ix_system_settings_key ON public.system_settings USING btree (setting_key)`
- `system_settings_pkey`: `CREATE UNIQUE INDEX system_settings_pkey ON public.system_settings USING btree (id)`

### `users`

| 컬럼 | PostgreSQL 형식 | NULL | 기본값 |
|---|---|---|---|
| `id` | `bigint` | 불가 | `nextval('users_id_seq'::regclass)` |
| `username` | `character varying(50)` | 불가 | — |
| `name` | `character varying(100)` | 불가 | — |
| `email` | `character varying(255)` | 허용 | — |
| `password_hash` | `character varying(512)` | 불가 | — |
| `account_type` | `character varying(20)` | 불가 | — |
| `status` | `character varying(20)` | 불가 | — |
| `last_login_at` | `timestamp with time zone` | 허용 | — |
| `password_changed_at` | `timestamp with time zone` | 불가 | — |
| `created_at` | `timestamp with time zone` | 불가 | — |
| `updated_at` | `timestamp with time zone` | 불가 | — |
| `created_by` | `bigint` | 허용 | — |
| `updated_by` | `bigint` | 허용 | — |

**제약조건**

- CHECK `ck_users_account_type`: `CHECK (account_type::text = ANY (ARRAY['admin'::character varying, 'employee'::character varying]::text[]))`
- CHECK `ck_users_status`: `CHECK (status::text = ANY (ARRAY['active'::character varying, 'suspended'::character varying]::text[]))`
- PK `users_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uq_users_email`: `UNIQUE (email)`

**인덱스**

- `ix_users_username`: `CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username)`
- `uq_users_email`: `CREATE UNIQUE INDEX uq_users_email ON public.users USING btree (email)`
- `users_pkey`: `CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id)`
