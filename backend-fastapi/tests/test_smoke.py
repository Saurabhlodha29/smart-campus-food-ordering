"""
Smoke tests for the FastAPI foundation layer.

Tests 1–3 are pure unit tests (no DB required).
Test 4 (test_db_connects) and test 5 (test_alembic_no_drift) require a live DB.

PREREQUISITES before running the DB tests:
  1. Populate backend-fastapi/.env  (copy from repo root .env.example and fill in)
  2. Run: alembic stamp a1b2c3d4e5f6   (marks the existing DB at the baseline)
  3. Then: pytest tests/test_smoke.py -v

If running against a FRESH database instead:
  1. Fill in .env
  2. alembic upgrade head   (creates all 16 tables)
  3. pytest tests/test_smoke.py -v
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

# The backend-fastapi/ root, used for alembic subprocess cwd
BACKEND_DIR = pathlib.Path(__file__).parents[1]

# ── Unit tests (no DB) ────────────────────────────────────────────────────────


def test_settings_load() -> None:
    """Config module must import and construct Settings without ValidationError."""
    from app.config import settings

    # async_database_url must be a computed property that starts correctly
    assert settings.async_database_url.startswith("postgresql+asyncpg://") or (
        settings.DB_URL == ""  # allowed in CI without a real URL
    ), f"Unexpected URL scheme: {settings.async_database_url!r}"


def test_app_boots() -> None:
    """FastAPI app must instantiate without error."""
    from app.main import app

    assert app.title == "Smart Campus Food Ordering"


def test_all_models_importable() -> None:
    """All 16 SQLAlchemy models must import cleanly and register with Base."""
    import app.models  # noqa: F401

    from app.db import Base

    table_names = set(Base.metadata.tables.keys())
    expected = {
        "roles",
        "campuses",
        "users",
        "outlets",
        "menu_items",
        "pickup_slots",
        "orders",
        "order_items",
        "payments",
        "outlet_payouts",
        "outlet_ratings",
        "notifications",
        "email_otp_tokens",
        "admin_applications",
        "outlet_applications",
        "verification_reports",
    }
    missing = expected - table_names
    assert not missing, f"Models not registered with Base: {missing}"


# ── Live-DB tests (require populated .env) ────────────────────────────────────


@pytest.mark.asyncio
async def test_db_connects() -> None:
    """
    The async engine must reach the DB and execute a trivial query.
    Skipped gracefully if DB_URL is empty (CI without a real DB).
    """
    from app.config import settings

    if not settings.DB_URL:
        pytest.skip("DB_URL not set — skipping live DB test")

    from sqlalchemy import text

    from app.db import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


def test_alembic_no_drift() -> None:
    """
    Verify Alembic models match the live schema with zero pending migrations.

    Requires the DB to have been stamped: alembic stamp a1b2c3d4e5f6
    A non-zero exit code means the SQLAlchemy models do not match the DB —
    investigate with: alembic upgrade --sql head
    """
    from app.config import settings

    if not settings.DB_URL:
        pytest.skip("DB_URL not set — skipping Alembic drift check")

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_DIR),
    )
    if result.returncode != 0:
        pytest.fail(
            "Alembic drift detected — SQLAlchemy models do not match the live schema.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n\n"
            "Fix: update the model + write a new migration, then re-run."
        )
