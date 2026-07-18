"""
Menu Items & Pickup Slots module tests — covers spec §4.4 (optimistic locking),
§9 (authorization matrix), MIGRATION_RULES §6 (layered architecture), and the
PickupSlot @Version behaviour ported via SQLAlchemy ``version_id_col``.

REQUIRED TEST LIST (from Prompt 4 migration task):
  - MANAGER create/update/delete/toggle-availability happy path
  - Student sees only available items (out-of-stock hidden)
  - Manager not owning outlet → 403 on every mutation
  - ADMIN can read /all on own campus, MANAGER can read /all on own outlet
  - Suspended outlet → create blocked with 400
  - Slot create validation (endTime > startTime, maxOrders >= 1)
  - Slot delete blocked when currentOrders > 0
  - Slot capacity update blocked when maxOrders < currentOrders
  - Slot adjust-count, newCount >= 0 enforced
  - GET /slots returns today only, GET /slots/upcoming returns today + future
  - Genuine concurrency: N students reserve against a 1-capacity slot
    via asyncio.gather — exactly one wins, others get 409
  - Role gating: STUDENT cannot POST/PATCH/DELETE; unauthenticated → 401

All tests run against the in-memory SQLite test database (see conftest.py).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.campus import Campus
from app.models.menu_item import MenuItem
from app.models.outlet import Outlet
from app.models.pickup_slot import PickupSlot
from app.models.role import Role
from app.models.user import User
from app.security.jwt import generate_token
from app.security.password import hash_password


# ──────────────────────────────────────────────────────────────────────────────
# Test scaffolding — create users + outlets + tokens directly in the DB
# ──────────────────────────────────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    email: str,
    role_name: str,
    campus: Campus | None,
    full_name: str = "Test User",
) -> User:
    """Insert a user with the given role + campus and return it."""
    role = (
        await db.execute(select(Role).where(Role.name == role_name))
    ).scalar_one()
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password("password123"),
        role=role,
        campus=campus,
        is_active=True,
        no_show_count=0,
        pending_penalty_amount=0.0,
        account_status="ACTIVE",
        created_at=datetime.now(),
    )
    db.add(user)
    await db.flush()
    return user


async def _make_outlet(
    db: AsyncSession,
    name: str,
    campus: Campus,
    manager: User,
    status: str = "ACTIVE",
) -> Outlet:
    """Insert an outlet owned by ``manager`` on ``campus``."""
    outlet = Outlet(
        name=name,
        campus_id=campus.id,
        manager_id=manager.id,
        status=status,
        avg_prep_time=15,
        photo_url=None,
        launched_at=datetime.now(),
        created_at=datetime.now(),
        opening_time=time(9, 0),
        closing_time=time(22, 0),
    )
    db.add(outlet)
    await db.flush()
    return outlet


def _auth_header(user: User) -> dict[str, str]:
    """Bearer header for ``user`` (token decoded via get_current_user)."""
    return {"Authorization": f"Bearer {generate_token(user.email, user.role.name)}"}


@pytest.fixture
async def world(seeded_db: AsyncSession) -> dict[str, Any]:
    """Pre-built world with two campuses, two managers, one admin, one student.

    Layout:
      campus_a (Test Campus, from seeded_db)
        manager_a — owns outlet_a (ACTIVE)
        manager_a — owns outlet_a_suspended (SUSPENDED)
      campus_b (Other Campus)
        manager_b — owns outlet_b (ACTIVE)
      admin_a — ADMIN on campus_a
      student_a — STUDENT on campus_a
    """
    db = seeded_db
    campus_a = (
        await db.execute(select(Campus).where(Campus.email_domain == "testcampus.edu"))
    ).scalar_one()

    # Second campus for cross-campus isolation tests
    campus_b = Campus(
        name="Other Campus",
        location="Other Location",
        email_domain="other.edu",
        status="ACTIVE",
        created_at=datetime.now(),
    )
    db.add(campus_b)

    manager_a = await _make_user(db, "manager_a@testcampus.edu", "MANAGER", campus_a, "Manager A")
    manager_b = await _make_user(db, "manager_b@other.edu", "MANAGER", campus_b, "Manager B")
    admin_a = await _make_user(db, "admin_a@testcampus.edu", "ADMIN", campus_a, "Admin A")
    student_a = await _make_user(db, "student_a@testcampus.edu", "STUDENT", campus_a, "Student A")

    outlet_a = await _make_outlet(db, "Outlet A", campus_a, manager_a)
    outlet_a_suspended = await _make_outlet(
        db, "Outlet A Suspended", campus_a, manager_a, status="SUSPENDED"
    )
    outlet_b = await _make_outlet(db, "Outlet B", campus_b, manager_b)

    await db.commit()
    return {
        "campus_a": campus_a,
        "campus_b": campus_b,
        "manager_a": manager_a,
        "manager_b": manager_b,
        "admin_a": admin_a,
        "student_a": student_a,
        "outlet_a": outlet_a,
        "outlet_a_suspended": outlet_a_suspended,
        "outlet_b": outlet_b,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Menu items — happy-path lifecycle
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manager_creates_menu_item(client: AsyncClient, world: dict[str, Any]) -> None:
    """POST /api/menu-items — MANAGER creates item on own outlet → 201."""
    r = await client.post(
        "/api/menu-items",
        json={
            "name": "Veg Burger",
            "price": 80.0,
            "prepTime": 12,
            "outletId": world["outlet_a"].id,
            "photoUrl": "https://example.com/burger.jpg",
        },
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Veg Burger"
    assert body["price"] == 80.0
    assert body["prepTime"] == 12
    assert body["photoUrl"] == "https://example.com/burger.jpg"
    assert body["isAvailable"] is True  # default in-stock
    assert body["outlet"]["id"] == world["outlet_a"].id
    assert body["outlet"]["name"] == "Outlet A"
    assert "createdAt" in body
    assert "id" in body


@pytest.mark.asyncio
async def test_manager_full_lifecycle(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """Create → update → toggle availability → delete."""
    # 1. Create
    r = await client.post(
        "/api/menu-items",
        json={"name": "Pizza", "price": 150.0, "prepTime": 20, "outletId": world["outlet_a"].id},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 201
    item_id = r.json()["id"]

    # 2. Update (PATCH)
    r = await client.patch(
        f"/api/menu-items/{item_id}",
        json={"name": "Margherita Pizza", "price": 180.0},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Margherita Pizza"
    assert r.json()["price"] == 180.0
    # prepTime unchanged
    assert r.json()["prepTime"] == 20

    # 3. Toggle availability — mark out of stock
    r = await client.patch(
        f"/api/menu-items/{item_id}/availability",
        json={"available": False},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["isAvailable"] is False

    # 4. Toggle back in stock
    r = await client.patch(
        f"/api/menu-items/{item_id}/availability",
        json={"available": True},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["isAvailable"] is True

    # 5. Delete
    r = await client.delete(
        f"/api/menu-items/{item_id}", headers=_auth_header(world["manager_a"])
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Menu item deleted"

    # 6. Item is gone
    remaining = (
        await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    ).scalar_one_or_none()
    assert remaining is None


# ──────────────────────────────────────────────────────────────────────────────
# Menu items — student sees only available items
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_student_sees_only_available_items(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """GET /api/menu-items hides out-of-stock items from students."""
    db.add_all([
        MenuItem(
            outlet_id=world["outlet_a"].id,
            name="In-Stock Item",
            price=50.0,
            prep_time=10,
            is_available=True,
            created_at=datetime.now(),
        ),
        MenuItem(
            outlet_id=world["outlet_a"].id,
            name="Out-of-Stock Item",
            price=70.0,
            prep_time=15,
            is_available=False,
            created_at=datetime.now(),
        ),
    ])
    await db.commit()

    r = await client.get(
        f"/api/menu-items?outletId={world['outlet_a'].id}",
        headers=_auth_header(world["student_a"]),
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "In-Stock Item"


@pytest.mark.asyncio
async def test_manager_all_endpoint_shows_out_of_stock(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """GET /api/menu-items/all includes out-of-stock items (manager view)."""
    db.add_all([
        MenuItem(
            outlet_id=world["outlet_a"].id,
            name="Avail",
            price=50.0,
            prep_time=10,
            is_available=True,
            created_at=datetime.now(),
        ),
        MenuItem(
            outlet_id=world["outlet_a"].id,
            name="OOS",
            price=70.0,
            prep_time=15,
            is_available=False,
            created_at=datetime.now(),
        ),
    ])
    await db.commit()

    r = await client.get(
        f"/api/menu-items/all?outletId={world['outlet_a'].id}",
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    names = {i["name"] for i in r.json()}
    assert names == {"Avail", "OOS"}


# ──────────────────────────────────────────────────────────────────────────────
# Menu items — outlet-scoping & cross-campus isolation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manager_cannot_create_on_other_outlet(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """Manager B cannot create an item on Manager A's outlet → 403."""
    r = await client.post(
        "/api/menu-items",
        json={
            "name": "Cross Item",
            "price": 10.0,
            "prepTime": 5,
            "outletId": world["outlet_a"].id,
        },
        headers=_auth_header(world["manager_b"]),
    )
    assert r.status_code == 403
    assert "own outlet" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_manager_cannot_update_other_outlet_item(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """Manager B cannot PATCH an item belonging to Manager A → 403."""
    item = MenuItem(
        outlet_id=world["outlet_a"].id,
        name="A's Item",
        price=50.0,
        prep_time=10,
        is_available=True,
        created_at=datetime.now(),
    )
    db.add(item)
    await db.commit()

    r = await client.patch(
        f"/api/menu-items/{item.id}",
        json={"price": 1.0},
        headers=_auth_header(world["manager_b"]),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_read_all_on_own_campus(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """ADMIN sees items on their own campus's outlets."""
    db.add(MenuItem(
        outlet_id=world["outlet_a"].id,
        name="Campus A Item",
        price=50.0,
        prep_time=10,
        is_available=True,
        created_at=datetime.now(),
    ))
    await db.commit()

    # Admin A can read campus A items
    r = await client.get(
        f"/api/menu-items/all?outletId={world['outlet_a'].id}",
        headers=_auth_header(world["admin_a"]),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Campus A Item"

    # Admin A cannot read campus B items → 403
    r = await client.get(
        f"/api/menu-items/all?outletId={world['outlet_b'].id}",
        headers=_auth_header(world["admin_a"]),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_suspended_outlet_blocks_create(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """POST on a SUSPENDED outlet → 400."""
    r = await client.post(
        "/api/menu-items",
        json={
            "name": "X",
            "price": 10.0,
            "prepTime": 5,
            "outletId": world["outlet_a_suspended"].id,
        },
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 400
    assert "suspended" in r.json()["error"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Menu items — role gating
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_student_cannot_create_menu_item(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """STUDENT → POST /api/menu-items → 403."""
    r = await client.post(
        "/api/menu-items",
        json={
            "name": "X",
            "price": 10.0,
            "prepTime": 5,
            "outletId": world["outlet_a"].id,
        },
        headers=_auth_header(world["student_a"]),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_access_all_endpoint(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """STUDENT → GET /api/menu-items/all → 403."""
    r = await client.get(
        "/api/menu-items/all",
        headers=_auth_header(world["student_a"]),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_get_menu_items_401(client: AsyncClient) -> None:
    """No JWT → GET /api/menu-items → 401."""
    r = await client.get("/api/menu-items")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# Pickup slots — create validation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_slot_happy_path(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """POST /api/slots — valid slot → 201, slotDate derived from startTime."""
    start = datetime.now() + timedelta(hours=2)
    end = start + timedelta(hours=1)
    r = await client.post(
        "/api/slots",
        json={
            "outletId": world["outlet_a"].id,
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "maxOrders": 25,
        },
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["maxOrders"] == 25
    assert body["currentOrders"] == 0
    assert body["version"] == 0
    assert body["slotDate"] == start.date().isoformat()
    assert body["outlet"]["id"] == world["outlet_a"].id


@pytest.mark.asyncio
async def test_create_slot_endtime_must_be_after_starttime(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """endTime == startTime → 400."""
    start = datetime.now() + timedelta(hours=2)
    r = await client.post(
        "/api/slots",
        json={
            "outletId": world["outlet_a"].id,
            "startTime": start.isoformat(),
            "endTime": start.isoformat(),
            "maxOrders": 10,
        },
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 400
    assert "after" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_create_slot_maxorders_at_least_1(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """maxOrders == 0 → 400."""
    start = datetime.now() + timedelta(hours=2)
    end = start + timedelta(hours=1)
    r = await client.post(
        "/api/slots",
        json={
            "outletId": world["outlet_a"].id,
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "maxOrders": 0,
        },
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 400
    assert "maxorders" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_create_slot_outlet_not_found(client: AsyncClient, world: dict[str, Any]) -> None:
    """outletId pointing at nonexistent outlet → 404."""
    start = datetime.now() + timedelta(hours=2)
    end = start + timedelta(hours=1)
    r = await client.post(
        "/api/slots",
        json={
            "outletId": 999999,
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "maxOrders": 10,
        },
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Pickup slots — delete blocked when currentOrders > 0
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_slot_blocked_when_has_orders(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """DELETE /api/slots/{id} → 400 when currentOrders > 0."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=3,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    r = await client.delete(
        f"/api/slots/{slot.id}", headers=_auth_header(world["manager_a"])
    )
    assert r.status_code == 400
    assert "3" in r.json()["error"]


@pytest.mark.asyncio
async def test_delete_slot_empty_slot_ok(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """DELETE /api/slots/{id} → 200 when currentOrders == 0."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=0,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    r = await client.delete(
        f"/api/slots/{slot.id}", headers=_auth_header(world["manager_a"])
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Slot deleted"
    assert r.json()["slotId"] == slot.id


# ──────────────────────────────────────────────────────────────────────────────
# Pickup slots — adjust-count
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adjust_count_add_and_subtract(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """PATCH /api/slots/{id}/adjust-count — positive and negative adjustments."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=2,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    # Add 3 → newCount = 5
    r = await client.patch(
        f"/api/slots/{slot.id}/adjust-count",
        json={"adjustment": 3},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["previousCount"] == 2
    assert body["newCount"] == 5
    assert body["maxOrders"] == 10

    # Subtract 5 → newCount = 0
    r = await client.patch(
        f"/api/slots/{slot.id}/adjust-count",
        json={"adjustment": -5},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["newCount"] == 0


@pytest.mark.asyncio
async def test_adjust_count_cannot_go_negative(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """PATCH adjust-count that would take count below 0 → 400."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=1,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    r = await client.patch(
        f"/api/slots/{slot.id}/adjust-count",
        json={"adjustment": -5},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 400
    assert "below 0" in r.json()["error"]


# ──────────────────────────────────────────────────────────────────────────────
# Pickup slots — capacity update
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_capacity_happy_path(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """PATCH /api/slots/{id}/capacity — raise maxOrders above currentOrders."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=5,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    r = await client.patch(
        f"/api/slots/{slot.id}/capacity",
        json={"maxOrders": 30},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["maxOrders"] == 30


@pytest.mark.asyncio
async def test_update_capacity_below_current_orders(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """PATCH capacity with maxOrders < currentOrders → 400."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=8,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    r = await client.patch(
        f"/api/slots/{slot.id}/capacity",
        json={"maxOrders": 5},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 400
    assert "below" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_update_capacity_zero_rejected(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """PATCH capacity with maxOrders == 0 → 400."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=0,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()

    r = await client.patch(
        f"/api/slots/{slot.id}/capacity",
        json={"maxOrders": 0},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 400


# ──────────────────────────────────────────────────────────────────────────────
# Pickup slots — today vs upcoming filtering
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_today_vs_upcoming_slots(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """GET /slots returns today only; GET /slots/upcoming returns today + future."""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    db.add_all([
        PickupSlot(
            outlet_id=world["outlet_a"].id,
            start_time=datetime.combine(yesterday, time(10, 0)),
            end_time=datetime.combine(yesterday, time(11, 0)),
            slot_date=yesterday,
            max_orders=10, current_orders=0, created_at=datetime.now(),
        ),
        PickupSlot(
            outlet_id=world["outlet_a"].id,
            start_time=datetime.combine(today, time(10, 0)),
            end_time=datetime.combine(today, time(11, 0)),
            slot_date=today,
            max_orders=10, current_orders=0, created_at=datetime.now(),
        ),
        PickupSlot(
            outlet_id=world["outlet_a"].id,
            start_time=datetime.combine(tomorrow, time(10, 0)),
            end_time=datetime.combine(tomorrow, time(11, 0)),
            slot_date=tomorrow,
            max_orders=10, current_orders=0, created_at=datetime.now(),
        ),
    ])
    await db.commit()

    # GET /slots?outletId=X → today only
    r = await client.get(
        f"/api/slots?outletId={world['outlet_a'].id}",
        headers=_auth_header(world["student_a"]),
    )
    assert r.status_code == 200
    today_slots = r.json()
    assert len(today_slots) == 1
    assert today_slots[0]["slotDate"] == today.isoformat()

    # GET /slots/upcoming?outletId=X → today + future (excludes yesterday)
    r = await client.get(
        f"/api/slots/upcoming?outletId={world['outlet_a'].id}",
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    upcoming = r.json()
    assert len(upcoming) == 2
    dates = {s["slotDate"] for s in upcoming}
    assert dates == {today.isoformat(), tomorrow.isoformat()}


# ──────────────────────────────────────────────────────────────────────────────
# Pickup slots — role gating
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_student_cannot_create_slot(
    client: AsyncClient, world: dict[str, Any]
) -> None:
    """STUDENT → POST /api/slots → 403."""
    start = datetime.now() + timedelta(hours=2)
    r = await client.post(
        "/api/slots",
        json={
            "outletId": world["outlet_a"].id,
            "startTime": start.isoformat(),
            "endTime": (start + timedelta(hours=1)).isoformat(),
            "maxOrders": 10,
        },
        headers=_auth_header(world["student_a"]),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_get_slots_401(client: AsyncClient) -> None:
    """No JWT → GET /api/slots → 401."""
    r = await client.get("/api/slots")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# OPTIMISTIC LOCKING — genuine concurrency test
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_slot_reservation_genuine_concurrency(
    seeded_db: AsyncSession, world: dict[str, Any], engine: Any
) -> None:
    """N students reserve against a 1-capacity slot via asyncio.gather.

    This is the spec §4.4 concurrency test. The slot has maxOrders=1, so only
    ONE student should successfully increment currentOrders. The rest should
    receive a 409 conflict (or a 409/410 race outcome). After the dust settles,
    currentOrders on the slot must equal exactly 1 — never 2, never 0.

    This exercises the optimistic-lock retry path in
    ``slot_service.increment_slot_orders_with_retry``. Each concurrent task
    uses its OWN AsyncSession (separate transactions) so they genuinely
    race against each other.

    IMPORTANT: We do NOT go through the HTTP layer here because the FastAPI
    test client uses a single shared session (StaticPool :memory: SQLite),
    which serialises access and would hide the race. Instead we call the
    service function directly with one session per coroutine.
    """
    # Seed a slot with maxOrders=1 in the shared test session.
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=1,
        current_orders=0,
        created_at=datetime.now(),
    )
    seeded_db.add(slot)
    await seeded_db.commit()
    slot_id = slot.id

    # Each coroutine gets its own session — they share the same in-memory
    # SQLite DB via StaticPool (one connection), but each holds its own
    # transaction. SQLite's locking serialises writes, so the optimistic-lock
    # retry path kicks in: when task A commits, task B's StaleDataError on
    # commit triggers exactly one retry.
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def attempt_reservation() -> tuple[bool, str | None]:
        """Try to reserve once. Returns (success, error_message_if_any)."""
        from app.exceptions import ApiException
        from app.services.slot_service import increment_slot_orders_with_retry

        try:
            async with factory() as session:
                await increment_slot_orders_with_retry(slot_id, session)
                await session.commit()
            return True, None
        except ApiException as exc:
            return False, exc.message
        except Exception as exc:  # noqa: BLE001 — capture any race outcome
            return False, f"{type(exc).__name__}: {exc}"

    # Launch N=10 concurrent reservations against a 1-capacity slot.
    results = await asyncio.gather(*(attempt_reservation() for _ in range(10)))
    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]

    # Exactly one must succeed.
    assert len(successes) == 1, (
        f"Expected exactly 1 success, got {len(successes)}: {results}"
    )
    # The rest must fail with a conflict error.
    assert len(failures) == 9, (
        f"Expected 9 failures, got {len(failures)}: {results}"
    )
    for ok, msg in failures:
        assert msg is not None
        # Either "Slot is full" (checked capacity and it was already 1) or
        # "Slot update conflict" (lost the version race).
        assert "full" in msg.lower() or "conflict" in msg.lower(), (
            f"Unexpected failure message: {msg}"
        )

    # Final DB state: currentOrders == 1, version >= 1 (bumped by the winner).
    await seeded_db.refresh(slot)
    assert slot.current_orders == 1, (
        f"Expected currentOrders=1 after concurrent race, got {slot.current_orders}"
    )
    assert slot.version >= 1, (
        f"Expected version >= 1 after at least one successful update, got {slot.version}"
    )


@pytest.mark.asyncio
async def test_optimistic_lock_version_bumps_on_capacity_update(
    client: AsyncClient, world: dict[str, Any], db: AsyncSession
) -> None:
    """Every successful UPDATE bumps the version column (Hibernate @Version parity)."""
    slot = PickupSlot(
        outlet_id=world["outlet_a"].id,
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        slot_date=datetime.now().date(),
        max_orders=10,
        current_orders=0,
        created_at=datetime.now(),
    )
    db.add(slot)
    await db.commit()
    assert slot.version == 0

    # First capacity update → version 1
    r = await client.patch(
        f"/api/slots/{slot.id}/capacity",
        json={"maxOrders": 20},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["version"] == 1

    # Second capacity update → version 2
    r = await client.patch(
        f"/api/slots/{slot.id}/capacity",
        json={"maxOrders": 30},
        headers=_auth_header(world["manager_a"]),
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
