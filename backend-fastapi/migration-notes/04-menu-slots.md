# 04 — Menu Items & Pickup Slots

**Migration step:** 5 of 12 (spec §22)
**Date:** 2026-07-18
**Status:** awaiting manual review

---

## What was done

- **Schemas** (`app/schemas/menu_item.py`, `app/schemas/pickup_slot.py`) — Pydantic v2 request/response models with camelCase aliases matching the Java DTOs + raw entity serialisation. Nested `_OutletRef` reproduces Hibernate's lazy-proxy Jackson serialisation.
- **Services** (`app/services/menu_service.py`, `app/services/slot_service.py`) — pure business logic layer. Java had no `MenuItemService` (controller talked to repos directly); we extract a service for layered-architecture consistency (MIGRATION_RULES §6) and to centralise the `assertOwnsOutlet` / `assertAdminCampusMatch` guards.
- **Routers** (`app/routers/menu_item.py`, `app/routers/pickup_slot.py`) — thin parse → delegate → wrap layer. Routers commit; services only `flush()`.
- **Wired** into `app/main.py` via `include_router`.
- **Tests** (`tests/test_menu_slots.py`) — 27 tests including the genuine concurrency test (spec §4.4). All pass.
- **Model tweak** — added a custom `version_id_generator` lambda to `PickupSlot` so the version column matches Hibernate's `@Version` initial value exactly (0 on INSERT, not 1).

---

## Endpoints migrated (spec §9 — authorization matrix reproduced exactly)

### Menu items (`/api/menu-items`)

| Method | Path                       | Role              | Notes |
|--------|----------------------------|-------------------|-------|
| GET    | ``?outletId=X``            | any authenticated | Available items only (out-of-stock hidden) — students, ordering screen |
| GET    | ``/all?outletId=X``        | MANAGER / ADMIN   | All items including out-of-stock. MANAGER scoped to own outlet, ADMIN scoped to own campus |
| POST   | ````                       | MANAGER           | Add item to own outlet. Blocked if outlet SUSPENDED |
| PATCH  | ``/{id}``                  | MANAGER           | Partial update (name/price/prepTime/photoUrl) |
| DELETE | ``/{id}``                  | MANAGER           | Permanently remove |
| PATCH  | ``/{id}/availability``     | MANAGER           | Toggle available/out-of-stock (body: `{"available": false}`) |

### Pickup slots (`/api/slots`)

| Method | Path                       | Role              | Notes |
|--------|----------------------------|-------------------|-------|
| GET    | ``?outletId=X``            | any authenticated | Today's slots only |
| GET    | ``/upcoming?outletId=X``   | any authenticated | Today + future slots |
| POST   | ````                       | MANAGER           | Create slot. Validates endTime > startTime, maxOrders >= 1 |
| DELETE | ``/{id}``                  | MANAGER           | Blocked if currentOrders > 0 |
| PATCH  | ``/{id}/adjust-count``     | MANAGER           | Manual counter adjustment (body: `{"adjustment": 3}`) |
| PATCH  | ``/{id}/capacity``         | MANAGER           | Update maxOrders. Blocked if maxOrders < currentOrders |

---

## Optimistic locking — spec §4.4

The Java entity `PickupSlot.java` uses Hibernate `@Version` (`private Long version = 0L`). The SQLAlchemy port wires the equivalent via `__mapper_args__ = {"version_id_col": version, ...}` on the `PickupSlot` model.

### Hibernate parity subtlety: version starts at 0, not 1

Hibernate initialises `@Version` to the declared field value (`0L`) on INSERT, then bumps to 1 on the first UPDATE. SQLAlchemy's **default** `version_id_generator` returns `1` for `None` (a fresh instance), which would make newly-inserted rows start at `version=1` — diverging from the Java wire format visible to clients.

Fixed with a custom generator in `app/models/pickup_slot.py`:

```python
__mapper_args__ = {
    "version_id_col": version,
    "version_id_generator": lambda v: 0 if v is None else v + 1,
}
```

Result: INSERT → 0, UPDATE → 1, UPDATE → 2, … — exact Hibernate parity. Verified by `test_optimistic_lock_version_bumps_on_capacity_update` and `test_create_slot_happy_path`.

### Retry logic

`slot_service.increment_slot_orders_with_retry(slot_id, db, max_retries=1)` is the concurrency-aware function that `OrderService` (next module) will call when a student places an order. It:
1. Loads the slot
2. Checks capacity (409 if full)
3. Increments `current_orders`
4. Flushes — SQLAlchemy bumps the version column automatically
5. On `StaleDataError` (version mismatch from another concurrent transaction), reloads and retries exactly once (spec §4.4 "one retry on conflict")

The menu/slot write operations in this module (create/delete/adjust/capacity) are manager-only single-actor — they don't need retry logic. The concurrent race happens when multiple students place orders simultaneously against the same slot, which is `OrderService` territory (next module).

---

## Genuine concurrency test (spec §4.4 — required)

`test_concurrent_slot_reservation_genuine_concurrency` in `tests/test_menu_slots.py`:

- Creates a slot with `maxOrders=1`, `currentOrders=0`
- Launches **10 concurrent** reservation attempts via `asyncio.gather`
- Each coroutine uses its **own** `AsyncSession` (separate transactions, sharing the in-memory SQLite DB via `StaticPool`)
- Asserts **exactly 1 success**, **9 failures** (either "Slot is full" or "Slot update conflict")
- Asserts final DB state: `currentOrders == 1`, `version >= 1`

### Why direct service calls, not HTTP

The FastAPI test client's `get_db` override returns the same shared session to every request. With SQLite's `StaticPool` (one connection), that serialises access and would hide the race. Calling `increment_slot_orders_with_retry` directly with one session per coroutine makes the transactions genuinely race — the optimistic-lock retry path is actually exercised.

### Actual test output

```
tests/test_menu_slots.py::test_concurrent_slot_reservation_genuine_concurrency PASSED

============================== 1 passed in 0.94s ==============================
```

Full test-file run:

```
============================= 27 passed in 23.36s =============================
```

---

## Not migrated (per spec §22 migration order — later modules)

| Java route / class                         | Reason                                                   | Module |
|--------------------------------------------|----------------------------------------------------------|--------|
| `GET /api/menu-items/search?q=`            | Not called by frontend (`api-endpoints.js`)              | —      |
| `GET /api/menu-items/recommendations`      | ML integration                                           | 9      |
| `GET /api/menu-items/outlet/{outletId}`    | Not called by frontend (students use `?outletId=`)       | —      |
| `PickupSlotService.cleanupPastSlots()`     | APScheduler cron job (`0 5 0 * * *`) — nightly cleanup   | 10     |
| `PickupSlotRepository.findById @Lock(PESSIMISTIC_WRITE)` | Not used by any controller in this module — was for `OrderService` pessimistic fallback (now superseded by optimistic lock + retry) | — |

---

## Divergences from Spring (all documented, none behavioural)

1. **Layered architecture for menu items**: Java `MenuItemController` had no service class (called repos directly). We add `menu_service.py` for consistency with other modules. No behaviour change.

2. **Slot ownership not checked on writes**: The Java `PickupSlotController` did **not** verify outlet ownership on create/delete/adjust/capacity — `SecurityConfig` only gated by role (`MANAGER`). So any MANAGER could manage any outlet's slots. Per MIGRATION_RULES (don't silently "fix"), this gap is preserved. The menu-item controller DID check ownership (`assertOwnsOutlet`); the slot controller did not. The asymmetry is intentional in the original code.

3. **`version_id_generator` customised**: SQLAlchemy's default would have made new rows start at version=1; Hibernate starts at 0. Custom lambda restores parity. No client-visible behaviour change beyond matching the original wire format.

4. **Concurrent capacity increment is in this module's service, called by next module**: `increment_slot_orders_with_retry` lives in `slot_service.py` so it can be tested in isolation here, but `OrderService` (next module) will import and call it when placing orders. This is the only cross-module coupling in this module.

---

## Files added/modified

| File                                            | Status   | Purpose |
|-------------------------------------------------|----------|---------|
| `app/schemas/menu_item.py`                      | added    | Pydantic schemas |
| `app/schemas/pickup_slot.py`                    | added    | Pydantic schemas |
| `app/services/menu_service.py`                  | added    | Business logic |
| `app/services/slot_service.py`                  | added    | Business logic + optimistic-lock retry helper |
| `app/routers/menu_item.py`                      | added    | 6 endpoints |
| `app/routers/pickup_slot.py`                    | added    | 6 endpoints |
| `app/models/pickup_slot.py`                     | modified | Added `version_id_generator` for Hibernate parity |
| `app/main.py`                                   | modified | Wired two new routers |
| `tests/test_menu_slots.py`                      | added    | 27 tests |

---

## Lint / type-check status

- **ruff**: clean on all 9 new/modified files
- **mypy**: clean on all 6 new files (7 pre-existing errors in `config.py`/`jwt.py` are unrelated to this module and were present before)
- **pytest**: 27/27 pass on `test_menu_slots.py`; full suite 56 pass, 1 skip, 2 pre-existing smoke-test failures (require unreachable dev DB)

---

## Stop point

**Stop and wait for manual review before: starting Orders.**

Orders depends directly on this module's capacity-check correctness — the `increment_slot_orders_with_retry` function and the `version_id_col` optimistic-lock behaviour must be reviewed before `OrderService` is built on top of them.
