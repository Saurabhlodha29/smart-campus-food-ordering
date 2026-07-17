"""
pytest configuration for the FastAPI backend test suite.

All tests in this suite are async (pytest-asyncio with asyncio_mode = "auto"
in pyproject.toml).

TEST DATABASE STRATEGY
----------------------
The dev Supabase database may be unreachable from CI / local machines (the
existing .env points at a pooler that requires an active project, which can
be paused). Tests therefore run against an **in-memory SQLite** database by
default — schema created via Base.metadata.create_all, no Alembic, no
network call.

A separate fixture (`dev_db_password_hash`) is provided for tests that
explicitly need to verify behaviour against the real dev database (e.g. the
BCrypt hash-compatibility witness). It skips cleanly when the dev DB is
unreachable.

The SQLite schema is created fresh for each test function and dropped after,
so tests are fully isolated — no shared state, no manual cleanup.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

# ── Schema bootstrap ───────────────────────────────────────────────────────────
# Base.metadata must include all 16 models. Importing ``app.models`` registers
# every model by side effect, populating Base.metadata before create_all runs.
import app.models  # noqa: F401 — side-effect import registers all models
from app.db import Base
from app.models.campus import Campus
from app.models.role import Role

# ── SQLite BigInteger → INTEGER autoincrement shim ─────────────────────────────
# Prod models declare ``BigInteger`` PKs to match Hibernate's ``bigint generated
# by default as identity``. SQLite's autoincrement contract requires
# ``INTEGER PRIMARY KEY`` — BIGINT PKs disable rowid autoincrement and inserts
# fail with NOT NULL constraint violations.
#
# Register a compile hook that emits ``INTEGER`` for BigInteger only on the
# SQLite dialect used by the test engine. Prod Postgres column types stay
# untouched (still BIGINT). This is a test-only shim; the prod models and
# Alembic migration are not modified by it.


@compiles(BigInteger, "sqlite")
def _bigint_for_sqlite(element: BigInteger, compiler: Any, **kw: Any) -> str:
    """Render BigInteger as INTEGER on SQLite so INTEGER PRIMARY KEY autoincrement works."""
    return "INTEGER"


# ── In-memory SQLite engine + session factory (per-test) ───────────────────────
# StaticPool keeps a single connection alive so :memory: persists across the
# session's multiple .execute() calls. PRAGMA foreign_keys=ON enforces FK
# constraints so the tests catch any FK violation a real Postgres would.


@pytest.fixture
async def engine():
    """Per-test in-memory SQLite async engine with FK enforcement on."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Enable FK enforcement on every new SQLite connection
    @event.listens_for(eng.sync_engine, "connect")
    def _enable_fk(dbapi_conn: Any, _: Any) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session bound to the in-memory SQLite engine."""
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session


# ── Seeded reference data ──────────────────────────────────────────────────────
# Most auth tests need at least: 4 roles + an ACTIVE campus with an email
# domain. We keep this fixture minimal (roles + one campus) and let tests that
# need a verified user build their own via the public /register endpoint.

@pytest.fixture
async def seeded_db(db: AsyncSession) -> AsyncSession:
    """db fixture with the 4 roles + a single ACTIVE campus pre-inserted."""
    db.add(Role(name="SUPERADMIN"))
    db.add(Role(name="ADMIN"))
    db.add(Role(name="MANAGER"))
    db.add(Role(name="STUDENT"))
    db.add(
        Campus(
            name="Test Campus",
            location="Test Location",
            email_domain="testcampus.edu",
            status="ACTIVE",
            created_at=datetime.now(),
        )
    )
    await db.flush()
    return db


# ── Mocked email sender ────────────────────────────────────────────────────────
# Tests must not hit real SMTP. We monkeypatch email_service.send_otp_email to
# record calls without sending. The OTP itself is preserved in the DB and in
# the DEBUG print, so tests can still assert on it.

@pytest.fixture
def mock_email(monkeypatch) -> list[dict[str, str]]:
    """Replace email_service.send_otp_email with a recorder. Returns the call log.

    otp_service.generate_and_send_otp awaits send_otp_email directly (no longer
    via FastAPI BackgroundTasks), so patching the symbol in otp_service's
    namespace is sufficient. We also patch the original email_service module for
    any future caller that imports it directly.
    """
    calls: list[dict[str, str]] = []

    async def _fake_send(to_email: str, full_name: str, otp_code: str) -> None:
        calls.append({"to": to_email, "name": full_name, "otp": otp_code})

    import app.services.email_service as email_svc
    import app.services.otp_service as otp_svc

    monkeypatch.setattr(email_svc, "send_otp_email", _fake_send)
    monkeypatch.setattr(otp_svc, "send_otp_email", _fake_send)
    return calls


# ── HTTP test client ───────────────────────────────────────────────────────────
# Overrides the get_db dependency so every request runs against the in-memory
# SQLite session. The email send is mocked via mock_email, so no real I/O
# happens.

@pytest.fixture
async def client(
    seeded_db: AsyncSession, mock_email: list[dict[str, str]]
) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wired to the FastAPI app with get_db overridden."""
    from app.db import get_db
    from app.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        # Return the seeded session (already has roles + campus). The test owns
        # the session's lifecycle — we don't close it here so the test can
        # inspect DB state after the request returns.
        yield seeded_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Dev-DB witness fixture (skips when unreachable) ──────────────────────────
# Used only by test_bcrypt_hash_compatibility_from_dev_db. Connects to the
# real Supabase dev DB to pull a stored password_hash. Skips if the DB is
# unreachable (e.g. paused project, no .env, CI without secrets).

@pytest.fixture
async def dev_db_password_hash() -> str:
    """
    Yield a real password_hash from the dev DB's users table.

    Skips the test using this fixture if the dev DB is unreachable — so the
    compatibility witness only runs where a live dev DB is available.
    """
    from app.config import settings

    if not settings.DB_URL:
        pytest.skip("DB_URL not set — skipping dev-DB BCrypt witness test")

    import asyncpg

    # Build direct asyncpg connection params from settings (skip SQLAlchemy
    # layer — we just want one row). Parse the JDBC URL manually.
    raw = settings.DB_URL.strip()
    if raw.startswith("jdbc:"):
        raw = raw[5:]
    # strip scheme
    rest = raw.split("://", 1)[1] if "://" in raw else raw
    # host:port/db?...
    host_port_db, _, _ = rest.partition("?")
    host_port, _, db_name = host_port_db.partition("/")
    host, _, port = host_port.partition(":")
    port_i = int(port) if port else 5432
    user = settings.DB_USERNAME or "postgres"
    password = settings.DB_PASSWORD or ""

    try:
        conn = await asyncpg.connect(
            host=host,
            port=port_i,
            user=user,
            password=password,
            database=db_name or "postgres",
            statement_cache_size=0,
            timeout=10,
        )
    except Exception as e:
        pytest.skip(f"Dev DB unreachable — skipping BCrypt witness: {type(e).__name__}: {e}")
        # unreachable — pytest.skip raises, but keep mypy/linter happy
        return ""

    try:
        row = await conn.fetchrow("SELECT password_hash FROM users LIMIT 1")
        if row is None:
            pytest.skip("Dev DB has no users — cannot witness BCrypt hash")
        return row["password_hash"]
    finally:
        await conn.close()


# ── Misc ───────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
