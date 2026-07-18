"""Menu item service — business logic for the menu-item endpoints.

Source of truth: ``MenuItemController.java`` (Spring Boot). The Java controller
had no separate service class — it called repositories directly. We keep a thin
service for consistency with other modules (application_service, auth_service)
and to centralise the outlet-ownership checks.

WHAT'S PRESERVED FAITHFULLY
---------------------------
- ``GET /api/menu-items?outletId=X`` — returns available items only (students).
- ``GET /api/menu-items/all?outletId=X`` — returns all items (MANAGER own outlet,
  ADMIN own campus).
- ``POST /api/menu-items`` — MANAGER only, scoped to own outlet, blocked if
  outlet is SUSPENDED.
- ``PATCH /api/menu-items/{id}`` — MANAGER only, partial update, scoped to own outlet.
- ``DELETE /api/menu-items/{id}`` — MANAGER only, scoped to own outlet.
- ``PATCH /api/menu-items/{id}/availability`` — MANAGER only, scoped to own outlet.
- ``assertOwnsOutlet`` — 403 if caller is not the manager of the target outlet.
- ``assertAdminCampusMatch`` — 403 if admin's campus != outlet's campus.
- ``isAvailable`` defaults to ``True`` (Java primitive boolean default).

NOT MIGRATED (per spec §22 migration order)
-------------------------------------------
- ``GET /api/menu-items/search`` — not called by frontend (no route in api-endpoints.js).
- ``GET /api/menu-items/recommendations`` — ML integration, Module 9.
- ``GET /api/menu-items/outlet/{outletId}`` — not called by frontend (students use
  ``?outletId=X`` query param via ``API.MENU(outletId)``).

TRANSACTION MODEL
-----------------
All mutating functions use ``db.flush()`` only — the router (FastAPI
dependency that owns the AsyncSession) commits on success.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ApiException
from app.models.menu_item import MenuItem
from app.models.outlet import Outlet


# ── Outlet ownership guards ──────────────────────────────────────────────────


def assert_owns_outlet(manager: Any, outlet: Outlet) -> None:
    """Throws 403 if the caller is not the manager of this outlet.

    Mirrors ``MenuItemController.assertOwnsOutlet()``.
    """
    if outlet.manager_id != manager.id:
        raise ApiException("You can only manage items for your own outlet", 403)


def assert_admin_campus_match(admin: Any, outlet: Outlet) -> None:
    """Throws 403 if the admin's campus does not match the outlet's campus.

    Mirrors ``MenuItemController.assertAdminCampusMatch()``.
    """
    if admin.campus_id is None or admin.campus_id != outlet.campus_id:
        raise ApiException("You can only view outlets on your own campus", 403)


# ── Public read: available items (any authenticated user) ────────────────────


async def get_available_menu_items(
    outlet_id: int | None, db: AsyncSession
) -> list[MenuItem]:
    """``GET /api/menu-items?outletId=X`` — available items for students.

    If outletId is provided, returns only available items for that outlet.
    If not, returns all available items (admin/debug use).
    Mirrors ``MenuItemController.getMenuItems()``.
    """
    stmt = select(MenuItem).where(MenuItem.is_available.is_(True))
    if outlet_id is not None:
        stmt = stmt.where(MenuItem.outlet_id == outlet_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Shared read: all items (MANAGER / ADMIN) ────────────────────────────────


async def get_all_menu_items(
    outlet_id: int | None, caller: Any, db: AsyncSession
) -> list[MenuItem]:
    """``GET /api/menu-items/all?outletId=X`` — all items including out-of-stock.

    MANAGER: scoped to own outlet.
    ADMIN: scoped to own campus.
    Mirrors ``MenuItemController.getAllMenuItems()``.
    """
    role_name = caller.role.name
    is_admin = role_name == "ADMIN"
    is_manager = role_name == "MANAGER"

    if outlet_id is not None:
        outlet = await _get_outlet_or_404(outlet_id, db)
        if is_manager:
            assert_owns_outlet(caller, outlet)
        elif is_admin:
            assert_admin_campus_match(caller, outlet)
        stmt = select(MenuItem).where(MenuItem.outlet_id == outlet_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # No outletId supplied
    if is_manager:
        outlet_stmt = select(Outlet).where(Outlet.manager_id == caller.id)
        outlet_result = await db.execute(outlet_stmt)
        manager_outlet = outlet_result.scalar_one_or_none()
        if manager_outlet is None:
            return []
        item_stmt = select(MenuItem).where(MenuItem.outlet_id == manager_outlet.id)
        item_result = await db.execute(item_stmt)
        return list(item_result.scalars().all())

    if is_admin:
        if caller.campus_id is None:
            return []
        outlet_stmt = select(Outlet).where(Outlet.campus_id == caller.campus_id)
        outlet_result = await db.execute(outlet_stmt)
        outlets = list(outlet_result.scalars().all())
        if not outlets:
            return []
        outlet_ids = [o.id for o in outlets]
        item_stmt = select(MenuItem).where(MenuItem.outlet_id.in_(outlet_ids))
        item_result = await db.execute(item_stmt)
        return list(item_result.scalars().all())

    # Fallback (shouldn't happen with role gating, but matches Java)
    stmt = select(MenuItem)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Create (MANAGER) ────────────────────────────────────────────────────────


async def create_menu_item(
    outlet_id: int,
    name: str,
    price: float,
    prep_time: int,
    photo_url: str | None,
    manager: Any,
    db: AsyncSession,
) -> MenuItem:
    """``POST /api/menu-items`` — add item to own outlet (MANAGER only).

    Mirrors ``MenuItemController.createMenuItem()``:
      - outlet must exist
      - manager must own the outlet
      - outlet must not be SUSPENDED
    """
    outlet = await _get_outlet_or_404(outlet_id, db)
    assert_owns_outlet(manager, outlet)

    if outlet.status == "SUSPENDED":
        raise ApiException("Cannot add items to a suspended outlet", 400)

    item = MenuItem(
        outlet_id=outlet_id,
        name=name,
        price=price,
        prep_time=prep_time,
        photo_url=photo_url,
        is_available=True,
        created_at=datetime.now(),
    )
    db.add(item)
    await db.flush()
    return item


# ── Update (MANAGER) ────────────────────────────────────────────────────────


async def update_menu_item(
    item_id: int,
    name: str | None,
    price: float | None,
    prep_time: int | None,
    photo_url: str | None,
    manager: Any,
    db: AsyncSession,
) -> MenuItem:
    """``PATCH /api/menu-items/{id}`` — edit item (MANAGER only).

    Mirrors ``MenuItemController.updateMenuItem()``: partial update, only
    non-null fields applied. Manager must own the item's outlet.
    """
    item = await _get_menu_item_or_404(item_id, db)
    assert_owns_outlet(manager, item.outlet)

    if name is not None:
        item.name = name
    if price is not None:
        item.price = price
    if prep_time is not None:
        item.prep_time = prep_time
    if photo_url is not None:
        item.photo_url = photo_url

    await db.flush()
    return item


# ── Delete (MANAGER) ────────────────────────────────────────────────────────


async def delete_menu_item(item_id: int, manager: Any, db: AsyncSession) -> None:
    """``DELETE /api/menu-items/{id}`` — permanently remove item (MANAGER only).

    Mirrors ``MenuItemController.deleteMenuItem()``.
    """
    item = await _get_menu_item_or_404(item_id, db)
    assert_owns_outlet(manager, item.outlet)
    await db.delete(item)
    await db.flush()


# ── Toggle availability (MANAGER) ──────────────────────────────────────────


async def set_availability(
    item_id: int, available: bool, manager: Any, db: AsyncSession
) -> MenuItem:
    """``PATCH /api/menu-items/{id}/availability`` — toggle available/out-of-stock.

    Mirrors ``MenuItemController.setAvailability()``.
    """
    item = await _get_menu_item_or_404(item_id, db)
    assert_owns_outlet(manager, item.outlet)
    item.is_available = available
    await db.flush()
    return item


# ── Internal helpers ───────────────────────────────────────────────────────


async def _get_outlet_or_404(outlet_id: int, db: AsyncSession) -> Outlet:
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise ApiException("Outlet not found", 404)
    return outlet


async def _get_menu_item_or_404(item_id: int, db: AsyncSession) -> MenuItem:
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise ApiException("Menu item not found", 404)
    return item
