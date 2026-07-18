"""Pickup-slot router — ``/api/slots/*`` endpoints.

Source of truth: ``PickupSlotController.java`` (Spring Boot
``@RestController @RequestMapping("/api/slots")``).

Authorization (spec §9 — SecurityConfig.java):
  - Any authenticated:  GET  /api/slots
                        GET  /api/slots/upcoming
  - MANAGER only:       POST   /api/slots
                        DELETE /api/slots/{id}
                        PATCH  /api/slots/{id}/adjust-count
                        PATCH  /api/slots/{id}/capacity

The router is thin (parse → delegate to service → wrap in response model); no
business logic lives here (MIGRATION_RULES §6).

NOTE: The Java controller did NOT check outlet ownership on slot create/delete/
adjust/capacity — the security config only gated by role (MANAGER). We preserve
this behaviour exactly: any MANAGER can create/delete slots for any outlet.
This is a known gap that the Java code had, and per MIGRATION_RULES we don't
"fix" it silently.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.schemas.pickup_slot import (
    AdjustCountRequest,
    AdjustCountResponse,
    CapacityRequest,
    DeleteSlotResponse,
    SlotCreateRequest,
    SlotResponse,
)
from app.security.deps import get_current_user, require_role
from app.services import slot_service

router = APIRouter(prefix="/api/slots", tags=["slots"])


# ── GET /api/slots?outletId=X — today's slots (any authenticated) ──────────


@router.get("", response_model=list[SlotResponse])
async def get_today_slots(
    outlet_id: Optional[int] = Query(default=None, alias="outletId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SlotResponse]:
    """Today's slots for an outlet (students, ordering screen).

    Mirrors ``PickupSlotController.getTodaySlots()``.
    """
    slots = await slot_service.get_today_slots(outlet_id, db)
    return [SlotResponse.model_validate(s) for s in slots]


# ── GET /api/slots/upcoming?outletId=X — today + future ────────────────────


@router.get("/upcoming", response_model=list[SlotResponse])
async def get_upcoming_slots(
    outlet_id: Optional[int] = Query(default=None, alias="outletId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SlotResponse]:
    """Today + future slots for an outlet (manager view).

    Mirrors ``PickupSlotController.getUpcomingSlots()``.
    """
    slots = await slot_service.get_upcoming_slots(outlet_id, db)
    return [SlotResponse.model_validate(s) for s in slots]


# ── POST /api/slots — create (MANAGER only) ─────────────────────────────────


@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    body: SlotCreateRequest,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> SlotResponse:
    """Create a pickup slot (MANAGER only).

    Mirrors ``PickupSlotController.createSlot()``.
    """
    slot = await slot_service.create_slot(
        outlet_id=body.outlet_id,
        start_time=body.start_time,
        end_time=body.end_time,
        max_orders=body.max_orders,
        db=db,
    )
    await db.commit()
    return SlotResponse.model_validate(slot)


# ── DELETE /api/slots/{id} — delete (MANAGER only) ──────────────────────────


@router.delete("/{slot_id}", response_model=DeleteSlotResponse)
async def delete_slot(
    slot_id: int,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> DeleteSlotResponse:
    """Delete a specific slot (MANAGER only).

    Mirrors ``PickupSlotController.deleteSlot()``.
    """
    await slot_service.delete_slot(slot_id, db)
    await db.commit()
    # Use alias kwargs — matches the camelCase JSON output shape and keeps mypy happy
    return DeleteSlotResponse.model_validate(
        {"message": "Slot deleted", "slotId": slot_id}
    )


# ── PATCH /api/slots/{id}/adjust-count — adjust count (MANAGER) ─────────────


@router.patch("/{slot_id}/adjust-count", response_model=AdjustCountResponse)
async def adjust_slot_count(
    slot_id: int,
    body: AdjustCountRequest,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> AdjustCountResponse:
    """Manually adjust currentOrders (MANAGER only).

    Mirrors ``PickupSlotController.adjustSlotCount()``.
    """
    result = await slot_service.adjust_slot_count(slot_id, body.adjustment, db)
    await db.commit()
    # Use model_validate with a dict — matches the camelCase JSON output shape
    return AdjustCountResponse.model_validate(
        {
            "message": "Slot count adjusted",
            "slotId": slot_id,
            "previousCount": result["previous_count"],
            "newCount": result["new_count"],
            "maxOrders": result["max_orders"],
        }
    )


# ── PATCH /api/slots/{id}/capacity — update capacity (MANAGER) ─────────────


@router.patch("/{slot_id}/capacity", response_model=SlotResponse)
async def update_slot_capacity(
    slot_id: int,
    body: CapacityRequest,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> SlotResponse:
    """Update maxOrders (MANAGER only).

    Mirrors ``PickupSlotController.updateSlotCapacity()``.
    """
    slot = await slot_service.update_slot_capacity(
        slot_id, body.max_orders, db
    )
    await db.commit()
    return SlotResponse.model_validate(slot)
