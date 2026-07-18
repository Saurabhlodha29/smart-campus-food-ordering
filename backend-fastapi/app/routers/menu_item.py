"""Menu-item router — ``/api/menu-items/*`` endpoints.

Source of truth: ``MenuItemController.java`` (Spring Boot
``@RestController @RequestMapping("/api/menu-items")``).

Authorization (spec §9 — SecurityConfig.java):
  - Any authenticated:  GET  /api/menu-items
  - MANAGER or ADMIN:  GET  /api/menu-items/all
  - MANAGER only:      POST   /api/menu-items
                        PATCH  /api/menu-items/{id}
                        DELETE /api/menu-items/{id}
                        PATCH  /api/menu-items/{id}/availability

The router is thin (parse → delegate to service → wrap in response model); no
business logic lives here (MIGRATION_RULES §6).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.schemas.menu_item import (
    AvailabilityRequest,
    DeleteMessageResponse,
    MenuItemCreateRequest,
    MenuItemResponse,
    MenuItemUpdateRequest,
)
from app.security.deps import get_current_user, require_role
from app.services import menu_service

router = APIRouter(prefix="/api/menu-items", tags=["menu-items"])


# ── GET /api/menu-items?outletId=X — available items (any authenticated) ────


@router.get("", response_model=list[MenuItemResponse])
async def get_menu_items(
    outlet_id: Optional[int] = Query(default=None, alias="outletId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MenuItemResponse]:
    """Available menu items for an outlet (students, ordering screen).

    Mirrors ``MenuItemController.getMenuItems()``.
    """
    items = await menu_service.get_available_menu_items(outlet_id, db)
    return [MenuItemResponse.model_validate(i) for i in items]


# ── GET /api/menu-items/all?outletId=X — all items (MANAGER / ADMIN) ───────


@router.get("/all", response_model=list[MenuItemResponse])
async def get_all_menu_items(
    outlet_id: Optional[int] = Query(default=None, alias="outletId"),
    user: User = Depends(require_role("MANAGER", "ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> list[MenuItemResponse]:
    """Full item list including out-of-stock items (MANAGER / ADMIN).

    Mirrors ``MenuItemController.getAllMenuItems()``.
    """
    items = await menu_service.get_all_menu_items(outlet_id, user, db)
    return [MenuItemResponse.model_validate(i) for i in items]


# ── POST /api/menu-items — create (MANAGER only) ───────────────────────────


@router.post("", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    body: MenuItemCreateRequest,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> MenuItemResponse:
    """Add a new menu item to own outlet (MANAGER only).

    Mirrors ``MenuItemController.createMenuItem()``.
    """
    item = await menu_service.create_menu_item(
        outlet_id=body.outlet_id,
        name=body.name,
        price=body.price,
        prep_time=body.prep_time,
        photo_url=body.photo_url,
        manager=user,
        db=db,
    )
    await db.commit()
    return MenuItemResponse.model_validate(item)


# ── PATCH /api/menu-items/{id} — update (MANAGER only) ──────────────────────


@router.patch("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: int,
    body: MenuItemUpdateRequest,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> MenuItemResponse:
    """Edit item details (MANAGER only).

    Mirrors ``MenuItemController.updateMenuItem()``.
    """
    item = await menu_service.update_menu_item(
        item_id=item_id,
        name=body.name,
        price=body.price,
        prep_time=body.prep_time,
        photo_url=body.photo_url,
        manager=user,
        db=db,
    )
    await db.commit()
    return MenuItemResponse.model_validate(item)


# ── DELETE /api/menu-items/{id} — delete (MANAGER only) ────────────────────


@router.delete("/{item_id}", response_model=DeleteMessageResponse)
async def delete_menu_item(
    item_id: int,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> DeleteMessageResponse:
    """Permanently remove item (MANAGER only).

    Mirrors ``MenuItemController.deleteMenuItem()``.
    """
    await menu_service.delete_menu_item(item_id, user, db)
    await db.commit()
    return DeleteMessageResponse(message="Menu item deleted")


# ── PATCH /api/menu-items/{id}/availability — toggle (MANAGER only) ───────


@router.patch("/{item_id}/availability", response_model=MenuItemResponse)
async def set_availability(
    item_id: int,
    body: AvailabilityRequest,
    user: User = Depends(require_role("MANAGER")),
    db: AsyncSession = Depends(get_db),
) -> MenuItemResponse:
    """Toggle available/out-of-stock (MANAGER only).

    Mirrors ``MenuItemController.setAvailability()``.
    """
    item = await menu_service.set_availability(item_id, body.available, user, db)
    await db.commit()
    return MenuItemResponse.model_validate(item)
