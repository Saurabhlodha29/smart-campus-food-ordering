"""Pydantic request/response schemas for the menu-item endpoints.

Mirrors the Java DTOs and raw ``MenuItem`` entity serialization produced by
Spring Boot's ``MenuItemController`` so the frontend contract (camelCase JSON)
stays identical after the FastAPI migration.

Mirrored Java classes:
    - MenuItemRequest          -> MenuItemCreateRequest
    - MenuItemUpdateRequest   -> MenuItemUpdateRequest
    - MenuItem (entity)        -> MenuItemResponse (with nested _OutletRef)
    - Map<String, Boolean>     -> AvailabilityRequest
    - Map<String, String>     -> DeleteResponse
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ── Nested outlet reference (matches Hibernate lazy-load serialisation) ─────


class _OutletRef(BaseModel):
    """Minimal outlet data embedded in MenuItem JSON responses.

    Spring serialises the full ``Outlet`` entity (Hibernate proxy resolved
    by Jackson). The frontend only uses ``id`` and ``name``, but we include
    all non-sensitive fields for parity.
    """

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


class MenuItemCreateRequest(BaseModel):
    """Body for ``POST /api/menu-items`` (MANAGER only).

    Mirrors Java ``MenuItemRequest``: name, price, prepTime, outletId,
    photoUrl (optional). No bean-validation constraints in the Java original
    — all fields required except photoUrl.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    name: str
    price: float
    prep_time: int = Field(..., alias="prepTime")
    outlet_id: int = Field(..., alias="outletId")
    photo_url: Optional[str] = Field(default=None, alias="photoUrl")


class MenuItemUpdateRequest(BaseModel):
    """Body for ``PATCH /api/menu-items/{id}`` (MANAGER only).

    Mirrors Java ``MenuItemUpdateRequest``: all fields optional — only non-null
    values are applied. Price is ``Double`` (nullable) in Java, matching
    ``Optional[float]`` here.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    name: Optional[str] = None
    price: Optional[float] = None
    prep_time: Optional[int] = Field(default=None, alias="prepTime")
    photo_url: Optional[str] = Field(default=None, alias="photoUrl")


class AvailabilityRequest(BaseModel):
    """Body for ``PATCH /api/menu-items/{id}/availability`` (MANAGER only).

    Mirrors the raw ``Map<String, Boolean>`` body the Java controller read via
    ``body.get("available")``.
    """

    model_config = ConfigDict(populate_by_name=True)

    available: bool


# ── Response schemas ────────────────────────────────────────────────────────


class MenuItemResponse(BaseModel):
    """Serialised MenuItem entity returned by all menu-item endpoints.

    Matches the Hibernate/Jackson serialisation of the Java ``MenuItem``
    entity: all fields present, camelCase keys, nested ``outlet`` object.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: int
    outlet: _OutletRef
    name: str
    price: float
    prep_time: int = Field(..., alias="prepTime")
    photo_url: Optional[str] = Field(default=None, alias="photoUrl")
    is_available: bool = Field(..., alias="isAvailable")
    created_at: datetime = Field(..., alias="createdAt")


class DeleteMessageResponse(BaseModel):
    """Body for ``DELETE /api/menu-items/{id}``.

    Mirrors ``Map.of("message", "Menu item deleted")``.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    message: str
