# Alembic

Run Alembic commands from this `backend` directory.

Alembic reads `DATABASE_URL` through `app.core.config.settings`, which loads environment variables or `.env` when present. Do not store real passwords in `alembic.ini`.

Use migrations only against a local development PostgreSQL database until the production deployment process is planned, backed up, and approved.

```powershell
alembic --help
alembic current
alembic revision --autogenerate -m "create asset tables"
alembic upgrade head
```

Do not run `alembic upgrade head` against the NAS production database in this step.
