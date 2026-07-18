"""Pickup slot service — business logic for the pickup-slot endpoints.

Source of truth: ``PickupSlotController.java`` + ``PickupSlotService.java``
(Spring Boot).

WHAT'S PRESERVED FAITHFULLY
---------------------------
- ``GET /api/slots?outletId=X`` — today's slots only for an outlet.
- ``GET /api/slots/upcoming?outletId=X`` — today + future slots.
- ``POST /api/slots`` — create slot (MANAGER), validates endTime > startTime,
  maxOrders >= 1.
- ``DELETE /api/slots/{id}`` — MANAGER, blocked if currentOrders > 0.
- ``PATCH /api/slots/{id}/adjust-count`` — manual counter adjustment.
- ``PATCH /api/slots/{id}/capacity`` — update maxOrders, blocked if
  maxOrders < currentOrders.
- ``version_id_col`` on PickupSlot model (optimistic locking). The service
  layer does NOT retry on ``StaleDataError`` — that retry lives in
  ``OrderService`` (next module) because the concurrent conflict happens when
  multiple students place orders simultaneously against the same slot. This
  module's write operations (create, delete, adjust, capacity) are manager-only
  single-actor, so they don't need retry logic here.

NOT MIGRATED
------------
- ``PickupSlotService.cleanupPastSlots()`` — nightly scheduled cleanup.
  This is an APScheduler job (Module 10 / background tasks). The Java cron
  was ``0 5 0 * * *`` (00:05 daily), deleting slots where slotDate < today.

TRANSACTION MODEL
-----------------
All mutating functions use ``db.flush()`` only — the router commits.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ApiException
from app.models.outlet import Outlet
from app.models.pickup_slot import PickupSlot

logger = logging.getLogger(__name__)


# ── Read: today's slots ──────────────────────────────────────────────────────


async def get_today_slots(
    outlet_id: int | None, db: AsyncSession
) -> list[PickupSlot]:
    """``GET /api/slots?outletId=X`` — today's slots for an outlet.

    Mirrors ``PickupSlotController.getTodaySlots()``.
    """
    today = date.today()
    stmt = select(PickupSlot).where(PickupSlot.slot_date == today)
    if outlet_id is not None:
        stmt = stmt.where(PickupSlot.outlet_id == outlet_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Read: upcoming slots (today + future) ──────────────────────────────────


async def get_upcoming_slots(
    outlet_id: int | None, db: AsyncSession
) -> list[PickupSlot]:
    """``GET /api/slots/upcoming?outletId=X`` — today + future slots.

    Mirrors ``PickupSlotController.getUpcomingSlots()``.
    """
    today = date.today()
    stmt = select(PickupSlot).where(
        PickupSlot.slot_date >= today
    ).order_by(
        PickupSlot.slot_date.asc(),
        PickupSlot.start_time.asc(),
    )
    if outlet_id is not None:
        stmt = stmt.where(PickupSlot.outlet_id == outlet_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Create (MANAGER) ───────────────────────────────────────────────────────


async def create_slot(
    outlet_id: int,
    start_time: datetime,
    end_time: datetime,
    max_orders: int,
    db: AsyncSession,
) -> PickupSlot:
    """``POST /api/slots`` — create a slot (MANAGER only).

    Mirrors ``PickupSlotController.createSlot()``:
      - outlet must exist
      - endTime must be after startTime
      - maxOrders must be >= 1
      - slotDate derived from startTime
    """
    # Verify outlet exists (404 if not) — value unused, lookup is the check
    await _get_outlet_or_404(outlet_id, db)

    if end_time <= start_time:
        raise ApiException("endTime must be after startTime", 400)
    if max_orders < 1:
        raise ApiException("maxOrders must be at least 1", 400)

    slot = PickupSlot(
        outlet_id=outlet_id,
        start_time=start_time,
        end_time=end_time,
        slot_date=start_time.date(),
        max_orders=max_orders,
        current_orders=0,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.flush()
    return slot


# ── Delete (MANAGER) ────────────────────────────────────────────────────────


async def delete_slot(slot_id: int, db: AsyncSession) -> None:
    """``DELETE /api/slots/{id}`` — delete slot (MANAGER only).

    Mirrors ``PickupSlotController.deleteSlot()``:
    Blocked if currentOrders > 0.
    """
    slot = await _get_slot_or_404(slot_id, db)

    if slot.current_orders > 0:
        raise ApiException(
            f"Cannot delete a slot that already has {slot.current_orders} "
            f"order(s) assigned to it.",
            400,
        )

    await db.delete(slot)
    await db.flush()


# ── Adjust count (MANAGER) ──────────────────────────────────────────────────


async def adjust_slot_count(
    slot_id: int, adjustment: int, db: AsyncSession
) -> dict[str, Any]:
    """``PATCH /api/slots/{id}/adjust-count`` — manually adjust currentOrders.

    Mirrors ``PickupSlotController.adjustSlotCount()``:
      - adjustment is added to current_orders
      - new count must be >= 0
    Returns dict with previousCount, newCount, maxOrders for the response.
    """
    slot = await _get_slot_or_404(slot_id, db)

    new_count = slot.current_orders + adjustment
    if new_count < 0:
        raise ApiException(
            f"Cannot reduce count below 0. Current: {slot.current_orders}",
            400,
        )

    previous_count = slot.current_orders
    slot.current_orders = new_count
    await db.flush()

    return {
        "previous_count": previous_count,
        "new_count": new_count,
        "max_orders": slot.max_orders,
    }


# ── Update capacity (MANAGER) ──────────────────────────────────────────────


async def update_slot_capacity(
    slot_id: int, max_orders: int, db: AsyncSession
) -> PickupSlot:
    """``PATCH /api/slots/{id}/capacity`` — update maxOrders (MANAGER only).

    Mirrors ``PickupSlotController.updateSlotCapacity()``:
      - maxOrders must be >= 1
      - maxOrders must be >= currentOrders
    """
    slot = await _get_slot_or_404(slot_id, db)

    if max_orders < 1:
        raise ApiException("'maxOrders' must be at least 1", 400)
    if max_orders < slot.current_orders:
        raise ApiException(
            f"Cannot set maxOrders ({max_orders}) below current order count "
            f"({slot.current_orders})",
            400,
        )

    slot.max_orders = max_orders
    await db.flush()
    return slot


# ── Optimistic-lock retry helper (for OrderService — next module) ──────────

async def increment_slot_orders_with_retry(
    slot_id: int, db: AsyncSession, max_retries: int = 1
) -> PickupSlot:
    """Increment current_orders on a slot with optimistic-lock retry.

    This is the concurrency-aware function that OrderService will call when
    a student places an order. It:
      1. Loads the slot
      2. Checks capacity (409 if full)
      3. Increments current_orders
      4. Flushes — SQLAlchemy bumps the version column automatically
      5. On StaleDataError (version mismatch), reload and retry once

    The PickupSlot model already has ``version_id_col`` configured, so
    SQLAlchemy raises ``StaleDataError`` if another transaction updated
    the same row between our read and write.

    Provided here so the concurrency test in this module can exercise it
    directly. OrderService will import and call this.
    """
    from sqlalchemy.orm.exc import StaleDataError

    for attempt in range(max_retries + 1):
        slot = await _get_slot_or_404(slot_id, db)

        if slot.current_orders >= slot.max_orders:
            raise ApiException("Slot is full", 409)

        slot.current_orders += 1
        try:
            await db.flush()
            return slot
        except StaleDataError:
            if attempt >= max_retries:
                raise ApiException(
                    "Slot update conflict — please try again", 409
                )
            # Rollback the failed flush state, retry
            await db.rollback()
            logger.warning(
                "Optimistic lock conflict on slot %d, retry %d/%d",
                slot_id,
                attempt + 1,
                max_retries,
            )
    # Should never reach here, but mypy needs it
    raise ApiException("Slot update conflict — please try again", 409)


# ── Internal helpers ───────────────────────────────────────────────────────


async def _get_outlet_or_404(outlet_id: int, db: AsyncSession) -> Outlet:
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise ApiException("Outlet not found", 404)
    return outlet


async def _get_slot_or_404(slot_id: int, db: AsyncSession) -> PickupSlot:
    result = await db.execute(
        select(PickupSlot).where(PickupSlot.id == slot_id)
    )
    slot = result.scalar_one_or_none()
    if slot is None:
        raise ApiException("Slot not found", 404)
    return slot
