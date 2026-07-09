# 00 — Foundation Layer

**Migration step:** 1 of 12 (spec §22)
**Date:** 2026-07-06
**Status:** awaiting manual review

---

## What was done

- Created `backend-fastapi/` project skeleton (folder layout mirrors `CLAUDE_CODE_MASTER_GUIDE.md §2`).
- `pyproject.toml` / `requirements.txt` with all runtime + dev dependencies.
- `app/config.py` — pydantic-settings `Settings` class, every env var mapped below.
- `app/db.py` — async SQLAlchemy engine + `AsyncSessionLocal` + `Base`.
- `app/exceptions.py` — `ApiException` + `GlobalExceptionHandler` equivalent (exact JSON error shape preserved).
- `app/main.py` — FastAPI app factory, CORS middleware (wildcard + credentials, spec §4.6), exception handlers. No routers yet.
- **16 SQLAlchemy 2.0 models** (one file per entity, matching the JPA `domain/` package layout).
- Alembic configuration (`alembic.ini`, `alembic/env.py` with async engine support).
- Baseline migration `a1b2c3d4e5f6_baseline.py` — full DDL for all 16 tables, derived by reading JPA entity annotations directly.
- Smoke tests (`tests/test_smoke.py`): app boots, all models registered, optional live-DB connection, optional Alembic drift check.
- Stub files for `schemas/`, `routers/`, `services/`, `security/`, `jobs/`, `sse.py`.

---

## Environment variable mapping

Every variable from `.env.example` / `application.yml` is preserved exactly, so the existing `.env` works without edits.

| Spring `application.yml` key | Env var name | Python `Settings` field | Notes |
|---|---|---|---|
| `spring.datasource.url` | `DB_URL` | `DB_URL` | Accepts JDBC (`jdbc:postgresql://...`) or standard (`postgresql://...`) format; converted to `postgresql+asyncpg://` internally |
| `spring.datasource.username` | `DB_USERNAME` | `DB_USERNAME` | Injected into URL if creds not already embedded |
| `spring.datasource.password` | `DB_PASSWORD` | `DB_PASSWORD` | Same |
| `jwt.secret` | `JWT_SECRET` | `JWT_SECRET` | HS256 signing key |
| `jwt.expiration` | `JWT_EXPIRY_MS` | `JWT_EXPIRY_MS` | Default 86400000 (24 h) |
| `otp.secret` | `OTP_SECRET` | `OTP_SECRET` | HMAC-SHA256 secret for pickup OTP (spec §4.1) |
| `otp.expiry-minutes` | `OTP_EXPIRY_MINUTES` | `OTP_EXPIRY_MINUTES` | Default 10 |
| `razorpay.key-id` | `RAZORPAY_KEY_ID` | `RAZORPAY_KEY_ID` | |
| `razorpay.key-secret` | `RAZORPAY_KEY_SECRET` | `RAZORPAY_KEY_SECRET` | |
| `razorpay.webhook-secret` | `RAZORPAY_WEBHOOK_SECRET` | `RAZORPAY_WEBHOOK_SECRET` | Default `NOT_SET` |
| `razorpay.payout-account-number` | `RAZORPAY_PAYOUT_ACCOUNT` | `RAZORPAY_PAYOUT_ACCOUNT` | Default `NOT_SET` |
| `razorpay.payouts-enabled` | `RAZORPAY_PAYOUTS_ENABLED` | `RAZORPAY_PAYOUTS_ENABLED` | Default `false` |
| `spring.mail.username` | `MAIL_USERNAME` | `MAIL_USERNAME` | |
| `spring.mail.password` | `MAIL_PASSWORD` | `MAIL_PASSWORD` | |
| `superadmin.email` | `SUPERADMIN_EMAIL` | `SUPERADMIN_EMAIL` | Default `superadmin@smartcampus.dev` |
| `superadmin.password` | `SUPERADMIN_PASSWORD` | `SUPERADMIN_PASSWORD` | |
| `superadmin.fullname` | `SUPERADMIN_FULLNAME` | `SUPERADMIN_FULLNAME` | Default `Platform SuperAdmin` |
| `ml.service.url` | `ML_SERVICE_URL` | `ML_SERVICE_URL` | Default `http://localhost:8000` |
| `ml.service.enabled` | `ML_SERVICE_ENABLED` | `ML_SERVICE_ENABLED` | Default `true` |
| `ml.service.timeout-ms` | `ML_SERVICE_TIMEOUT_MS` | `ML_SERVICE_TIMEOUT_MS` | Default `3000` |
| `spring.data.redis.host` | `REDIS_HOST` | `REDIS_HOST` | Default `localhost` |
| `spring.data.redis.port` | `REDIS_PORT` | `REDIS_PORT` | Default `6379` |
| _(no Spring equivalent)_ | `ENVIRONMENT` | `ENVIRONMENT` | **NEW** — `"development"` enables `simulateOrderPayment` bypass (spec §4.10 security fix). Default `"production"` = bypass disabled. Add this to `.env` when running in dev mode. |

Frontend-only vars (`VITE_*`) are accepted and silently ignored (`extra = "ignore"`).

---

## Alembic baseline verification (required before proceeding)

The baseline migration `a1b2c3d4e5f6` was derived from the JPA entity annotations,
**not** from `docs/` (which is stale — spec §14).

### For the existing Supabase database (normal path)

```bash
cd backend-fastapi
pip install -e ".[dev]"

# 1. Mark the existing DB as already at the baseline (no DDL runs)
alembic stamp a1b2c3d4e5f6

# 2. Verify zero drift between SQLAlchemy models and live schema
alembic check

# 3. Run smoke tests
pytest tests/test_smoke.py -v
```

`alembic check` must report **"No new upgrade operations detected."**
If it reports drift, investigate each difference before proceeding — it
means either the JPA entity was misread or the live DB diverged from the
entity annotations (possible if Hibernate ran migrations while the code was
evolving).

### For a fresh database

```bash
alembic upgrade head   # creates all 16 tables
alembic check          # should report no drift
pytest tests/test_smoke.py -v
```

---

## Naming convention decisions (documented for review)

| Decision | Rationale |
|---|---|
| `SpringPhysicalNamingStrategy`: camelCase field → snake_case column | This is what the existing DB has; Hibernate applied it automatically. SQLAlchemy Python attrs use snake_case too, so they align naturally. |
| `password_hash VARCHAR(255)` | `@Column(nullable=false)` on a String without `length` → Hibernate default 255. BCrypt hash is 60 chars, fits comfortably. |
| `is_active`, `is_available`, `is_read` | Java primitive `boolean` field names `isActive`, `isAvailable`, `isRead` → snake_case `is_active`, `is_available`, `is_read`. SpringPhysicalNamingStrategy derives from field name, not getter. |
| `TEXT` for Base64 document columns | `@Column(columnDefinition = "TEXT")` in Java. These store full base64 image data-URIs (spec §4.5 — deliberate, not to be "fixed"). |
| `Double` type for all Java `double` fields | `sa.Double()` maps to `DOUBLE PRECISION` in PostgreSQL, matching Hibernate. `Decimal`-everywhere refactor is explicitly out of scope (spec §10). |
| `version` on `pickup_slots` → `version_id_col` | Exact equivalent of Hibernate `@Version`. SQLAlchemy's default version_id_generator increments by 1, same as Hibernate. Service layer must catch `StaleDataError` and retry once (spec §4.4) — implement in Orders module. |
| `order_source` explicit column name | Java has `@Column(name = "order_source")` — preserved. |
| `email_domain` explicit column name | Java has `@Column(name = "email_domain")` — preserved. |
| `penalty_user_id` explicit column name | Java has `@Column(name = "penalty_user_id")` — preserved. |

---

## What is NOT in this layer (per spec — stop here)

- No Pydantic schemas
- No routers / endpoints
- No service logic
- No JWT utilities
- No DataInitializer / SuperAdmin seeding (Auth module, step 2)
- No rate-limit middleware (Final integration, step 12)
- No SSE logic (Final integration, step 12)
- No APScheduler jobs (Background Jobs module, step 10)

---

## Flags for human review

1. **`ENVIRONMENT` variable is new** — not in the existing `.env.example`. It must be added to the `.env` file before the payment simulation bypass is relevant (step 7, Payments module). Default is `"production"` so the existing `.env` is safe as-is.

2. **Alembic `_include_object` skips reflected-only indexes** — Hibernate creates FK indexes named `FK...` that are not defined in our models. The `env.py` `_include_object()` function excludes reflected-only indexes from drift comparison. This means Hibernate-generated FK indexes won't cause false-positive drift warnings, but model-defined indexes that are missing from the DB *will* still be flagged. This is the correct behaviour. If you'd prefer to include FK index comparison, remove the `_include_object` filter and add explicit `Index(...)` declarations for each FK column.

3. **`password_hash` column length** — marked as `VARCHAR(255)` because `@Column(nullable=false)` on `String` without `length` → Hibernate default 255. If the live DB column is actually `TEXT` (possible if the schema was hand-edited), the smoke test's `alembic check` will flag it. Update the model + baseline migration accordingly.

4. **`pickup_slots.version` start value** — the SQLAlchemy `version_id_col` requires the column to be `NOT NULL`. Existing rows in the DB created by Hibernate will have `version = 0` (Hibernate starts at 0). Verify with: `SELECT MIN(version), MAX(version) FROM pickup_slots;` — if any rows have `NULL`, update them to `0` before running migrations.
