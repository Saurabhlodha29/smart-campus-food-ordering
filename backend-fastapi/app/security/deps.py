"""FastAPI auth dependencies — replaces the migration stub.

Replaces the placeholder added in migration step 2 with the full
implementation:

  - ``get_current_user``  → resolves the bearer token to a ``User`` row.
  - ``require_role``       → factory returning a role-checking dependency.

Role-name convention
--------------------
Spring applied the ``"ROLE_"`` prefix inside ``SimpleGrantedAuthority``
construction in ``JwtFilter.java`` — that prefix lived in the Spring Security
authority layer, never in the JWT token and never in the ``roles.name``
column. FastAPI has no Spring Security authority layer, so the bare role name
("SUPERADMIN", "ADMIN", "MANAGER", "STUDENT") is compared directly against
``allowed_roles``. This is the exact behavioural equivalent: the prefix was a
Spring-internal packaging detail, not an authorisation rule.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.exceptions import ApiException
from app.models.user import User
from app.security.jwt import decode_token

# auto_error=False so a missing Authorization header yields OUR ApiException
# shape ({timestamp, status, error}) rather than FastAPI's default 401 body.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the bearer token to the authenticated ``User``.

    Flow:
      1. Missing token → 401 "Authentication required".
      2. Token fails signature/expiry validation → decode_token raises 401
         "Invalid or expired token".
      3. Token decodes but the subject (email) no longer maps to a user row
         → 401 "User not found" (e.g. user deleted after token issued).
      4. Success → return the ``User`` instance with ``role`` already loaded
         (``User.role`` is configured ``lazy="joined"``).

    The ``role`` relationship is eager-loaded by SQLAlchemy, so callers may
    inspect ``user.role.name`` without an extra await/round-trip.
    """
    if token is None:
        raise ApiException("Authentication required", 401)

    claims: dict[str, Any] = decode_token(token)

    result = await db.execute(
        select(User).where(User.email == claims["sub"])
    )
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise ApiException("User not found", 401)

    return user


def require_role(*allowed_roles: str) -> Callable[..., Any]:
    """Build a FastAPI dependency that enforces one of ``allowed_roles``.

    Usage::

        @router.post("/admin/users", dependencies=[Depends(require_role("SUPERADMIN", "ADMIN"))])
        async def create_user(...): ...

    or applied as a per-route parameter dependency::

        async def handler(user: User = Depends(require_role("MANAGER"))) -> ...: ...

    The returned callable depends on :func:`get_current_user` and compares
    ``user.role.name`` (bare — e.g. ``"ADMIN"``) against the supplied
    ``allowed_roles``. The ``"ROLE_"`` prefix that Spring's
    ``SimpleGrantedAuthority`` added inside ``JwtFilter.java`` is NOT added
    here: that prefix was a Spring Security authority-layer convention only
    and never appeared in the JWT token or in the ``roles.name`` DB column.
    FastAPI has no Spring Security authority layer, so bare role-name
    comparison is the direct behavioural equivalent.
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in allowed_roles:
            raise ApiException("Access denied", 403)
        return user

    return role_checker
