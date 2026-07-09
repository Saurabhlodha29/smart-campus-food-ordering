"""
Alembic env.py — async configuration using asyncpg.

URL is injected from app.config.settings so the existing .env works unchanged.
All 16 models are imported via app.models to ensure Base.metadata is complete.

Index comparison note:
  Hibernate creates implicit FK indexes named FK_... that are not defined in
  our SQLAlchemy models.  _include_object() skips reflected-only indexes to
  prevent spurious drift warnings.  If a model-defined index is missing from
  the DB it is still flagged correctly.
"""
import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ── Load all models → Base.metadata ──────────────────────────────────────────
from app.db import Base
import app.models  # noqa: F401 — side-effect import registers all 16 models

target_metadata = Base.metadata

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")


def get_url() -> str:
    from app.config import settings
    return settings.async_database_url


def _include_object(
    obj: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object,
) -> bool:
    """
    Exclude indexes that exist only in the DB (Hibernate FK indexes).
    Model-defined indexes that are absent from the DB are still flagged.
    """
    if type_ == "index" and reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection (generates SQL script).
    Used by: alembic upgrade --sql head
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        include_object=_include_object,
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = get_url()
    connectable = create_async_engine(url, echo=False)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
