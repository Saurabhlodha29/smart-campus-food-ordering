"""
Startup seeding — port of DataInitializer.java's CommandLineRunner.

Run once on application startup (invoked from main.py's lifespan) to guarantee
the four fixed application roles and the platform SuperAdmin account exist.
Every INSERT is guarded by an existence check, so this is IDEMPOTENT and safe
to re-run on every boot — it will never create duplicate roles nor a second
SuperAdmin, mirroring the ifPresent/isEmpty guards in the Java original.

DIFFERENCE FROM SPRING
---------------------
Spring's CommandLineRunner ran inside the framework's startup transaction and
committed implicitly. Here we use an explicit db.commit() at the end because
this is a standalone startup routine with no outer HTTP request owning the
session — committing keeps the seeded rows durable and matches the Java intent
(seed data should persist across restarts of the same bootstrap, not vanish
if the session is discarded).

CONFIG SOURCES
--------------
- SUPERADMIN_EMAIL    (default: superadmin@smartcampus.dev)
- SUPERADMIN_PASSWORD (no default — intentionally empty, set via .env)
- SUPERADMIN_FULLNAME (default: Platform SuperAdmin)

If SUPERADMIN_PASSWORD is left blank, a BCrypt hash of the empty string will
still be produced by hash_password() — the account will simply fail to log in.
That's the same behaviour as the Java side (passwordEncoder.encode("") is a
valid hash that nothing verifies against). Intentionally no guard added here;
the deployment is expected to set the env var.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.role import Role
from app.models.user import User
from app.security.password import hash_password

logger = logging.getLogger(__name__)

# The four fixed application roles, matching the ensureRole(...) calls in
# DataInitializer.initData. Order is preserved for log readability but the
# insertion order in the DB is not semantically significant (each is a
# standalone row lookup by name).
APP_ROLES: tuple[str, ...] = ("SUPERADMIN", "ADMIN", "MANAGER", "STUDENT")


async def seed_roles_and_superadmin(db: AsyncSession) -> None:
    """Idempotent startup seeding.

    Seeds the four fixed roles (SUPERADMIN, ADMIN, MANAGER, STUDENT) and a
    single platform SuperAdmin user — only if each is absent. Safe to call
    on every startup: existence-check before every INSERT means no duplicates
    ever get created, exactly like the Java ifPresent / isEmpty guards.

    Args:
        db: An async session. The session is committed here because this is a
            startup routine with no enclosing request/transaction owner.

    Raises:
        RuntimeError: if the SUPERADMIN role is missing after the role-seeding
            pass — indicates a schema/config breakage that should fail fast
            and loudly rather than silently booting an unbootable system.
    """
    # ── 1. Roles ─────────────────────────────────────────────────────────────
    # Loop preserves the Java ordering (SUPERADMIN…STUDENT) for log parity,
    # though the final DB contents are identical regardless of order.
    for role_name in APP_ROLES:
        existing = (
            await db.execute(select(Role).where(Role.name == role_name))
        ).scalar_one_or_none()
        if existing is None:
            db.add(Role(name=role_name))
            logger.info("Role created: %s", role_name)

    await db.flush()  # make the new role rows visible to the SuperAdmin lookup below

    # ── 2. SuperAdmin (only if email not already present) ─────────────────────
    # Mirrors `if (userRepo.findByEmail(superadminEmail).isEmpty())`.
    existing_admin = (
        await db.execute(select(User).where(User.email == settings.SUPERADMIN_EMAIL))
    ).scalar_one_or_none()
    if existing_admin is None:
        superadmin_role = (
            await db.execute(select(Role).where(Role.name == "SUPERADMIN"))
        ).scalar_one_or_none()
        # If still None after the seeding pass above, the roles table is broken
        # or the schema is misconfigured — fail loudly rather than insert a
        # role-less SuperAdmin that nobody could ever look up.
        if superadmin_role is None:
            raise RuntimeError(
                "SUPERADMIN role missing after seeding — schema or config issue"
            )

        # SuperAdmin is not campus-scoped (campus=None), matching the Java
        # `new User(fullName, email, encodedPw, superadminRole, null)`.
        # account_status "ACTIVE" is set explicitly here for parity even though
        # the User model column already defaults to "ACTIVE".
        sa = User(
            full_name=settings.SUPERADMIN_FULLNAME,
            email=settings.SUPERADMIN_EMAIL,
            password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
            role=superadmin_role,  # SQLAlchemy populates role_id from the relationship
            campus=None,
            is_active=True,
            no_show_count=0,
            pending_penalty_amount=0.0,
            account_status="ACTIVE",
            created_at=datetime.now(),
        )
        db.add(sa)
        logger.info("SuperAdmin created: %s", settings.SUPERADMIN_EMAIL)

    # Commit the seeding — startup routine, no outer request owns this session.
    # Spring's CommandLineRunner committed implicitly via the framework tx; we
    # do it explicitly here because there's no enclosing FastAPI dependency.
    await db.commit()
