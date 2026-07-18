"""Pydantic request/response schemas for the pickup-slot endpoints.

Mirrors the Java DTOs and raw ``PickupSlot`` entity serialization produced by
Spring Boot's ``PickupSlotController`` so the frontend contract (camelCase JSON)
stays identical after the FastAPI migration.

Mirrored Java classes:
    - PickupSlotRequest       -> SlotCreateRequest
    - PickupSlot (entity)    -> SlotResponse (with nested _OutletRef)
    - Map<String, Integer>   -> AdjustCountRequest / CapacityRequest
    - Map<String, Object>    -> AdjustCountResponse
    - Map<String, String>    -> DeleteSlotResponse
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ── Nested outlet reference ───────────────────────────────────────────────


class _OutletRef(BaseModel):
    """Minimal outlet data embedded in PickupSlot JSON responses."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: int
    name: str
    campus_id: int = Field(..., alias="campusId")
    manager_id: int = Field(..., alias="managerId")
    status: str
    avg_prep_time: int = Field(..., alias="avgPrepTime")
    created_at: datetime = Field(..., alias="createdAt")


# ── Request schemas ─────────────────────────────────────────────────────────


class SlotCreateRequest(BaseModel):
    """Body for ``POST /api/slots`` (MANAGER only).

    Mirrors Java ``PickupSlotRequest``: outletId, startTime, endTime,
    maxOrders. Validation (endTime > startTime, maxOrders >= 1) is done
    at the service layer, matching the Java controller's manual checks.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    outlet_id: int = Field(..., alias="outletId")
    start_time: datetime = Field(..., alias="startTime")
    end_time: datetime = Field(..., alias="endTime")
    max_orders: int = Field(..., alias="maxOrders")


class AdjustCountRequest(BaseModel):
    """Body for ``PATCH /api/slots/{id}/adjust-count`` (MANAGER only).

    Mirrors the raw ``Map<String, Integer>`` body the Java controller read
    via ``body.get("adjustment")``. Positive = add, negative = remove.
    """

    model_config = ConfigDict(populate_by_name=True)

    adjustment: int


class CapacityRequest(BaseModel):
    """Body for ``PATCH /api/slots/{id}/capacity`` (MANAGER only).

    Mirrors the raw ``Map<String, Integer>`` body the Java controller read
    via ``body.get("maxOrders")``.
    """

    model_config = ConfigDict(populate_by_name=True)

    max_orders: int = Field(..., alias="maxOrders")


# ── Response schemas ────────────────────────────────────────────────────────


class SlotResponse(BaseModel):
    """Serialised PickupSlot entity returned by slot endpoints.

    Matches the Hibernate/Jackson serialisation of the Java ``PickupSlot``
    entity: all fields present, camelCase keys, nested ``outlet`` object.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: int
    outlet: _OutletRef
    start_time: datetime = Field(..., alias="startTime")
    end_time: datetime = Field(..., alias="endTime")
    slot_date: date = Field(..., alias="slotDate")
    max_orders: int = Field(..., alias="maxOrders")
    current_orders: int = Field(..., alias="currentOrders")
    created_at: datetime = Field(..., alias="createdAt")
    version: int


class AdjustCountResponse(BaseModel):
    """Body for ``PATCH /api/slots/{id}/adjust-count``.

    Mirrors the Map<String, Object> response with message, slotId,
    previousCount, newCount, maxOrders.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    message: str
    slot_id: int = Field(..., alias="slotId")
    previous_count: int = Field(..., alias="previousCount")
    new_count: int = Field(..., alias="newCount")
    max_orders: int = Field(..., alias="maxOrders")


class DeleteSlotResponse(BaseModel):
    """Body for ``DELETE /api/slots/{id}``.

    Mirrors ``Map.of("message", "Slot deleted", "slotId", String.valueOf(id))``.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    message: str
    slot_id: int = Field(..., alias="slotId")
