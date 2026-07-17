# MIGRATION_SPECIFICATION.md
### Smart Campus Food — Spring Boot → FastAPI Backend Migration
**Status:** Master specification. Every other migration document (rules, guide, prompts) derives its authority from this file.
**Ground truth policy:** This spec was built by reading the actual repository (`Saurabhlodha29/smart-campus-food-ordering`, `main`), not `docs/`. Where `docs/` disagrees with code, code wins — see §14.

---

## 1. Original Project Vision

A pickup-only, multi-campus food ordering platform for Indian college campuses — "Swiggy/Zomato for a campus, no delivery." A student orders ahead from a campus outlet, books a pickup slot, pays online or COD, and collects using a 4-digit OTP. The differentiating goals, in the founder's own words, are:

- Eliminate physical queues and peak-hour crowding at campus outlets.
- Spread demand across capacity-limited hourly pickup slots.
- Use ML to predict wait time and no-show risk.
- Penalize no-shows with a **demand-weighted** fine (not a flat fine) so the punishment reflects actual loss risk to the outlet.
- Give outlet managers a full operations toolkit: counter orders for walk-ins, a ledger, analytics, and automatic weekly payouts.

Four roles, strictly hierarchical and campus-scoped: **SUPERADMIN** (platform, seeded once) → **ADMIN** (one per campus, self-applies, approved by SUPERADMIN) → **MANAGER** (one per outlet, self-applies with documents, approved by ADMIN) → **STUDENT** (self-registers with a campus-domain email, OTP-verified).

This is currently a solo second-year-student project explicitly built with **free-tier services** (test Razorpay keys, free Postgres/Redis tiers, free SMTP relay) with a stated intent to swap in paid production equivalents later without changing business logic. The migration must not compromise that swap path.

---

## 2. Final Architecture (Post-Migration Target)

```
┌─────────────────────────────┐
│  Frontend (React + Vite)    │  — UNCHANGED. Same axios contracts, same routes, same JSON shapes.
└──────────────┬───────────────┘
               │ HTTPS, JWT Bearer
               ▼
┌──────────────────────────────────────────────────────────────┐
│  Unified FastAPI Backend  (replaces Spring Boot backend)     │
│  - Same REST surface, same paths, same verbs, same roles     │
│  - Pydantic request/response models replace raw entity JSON  │
│  - SQLAlchemy 2.0 (async) replaces Hibernate/JPA              │
│  - Same JWT shape (sub=email, role claim, HS256)              │
│  - Same rate-limit filter behavior (Redis + in-memory fallback)│
│  - Same SSE-over-Redis pub/sub for live order tracking        │
│  - APScheduler replaces @Scheduled (penalty expiry, payouts)  │
└──────────────┬───────────────────────────┬────────────────────┘
               │ shared Postgres DB          │ internal HTTP (unchanged contract)
               ▼                             ▼
        PostgreSQL (Supabase)         ML microservice (FastAPI, already Python — UNTOUCHED)
               ▲
               │ raw SQL / SQLAlchemy reads (shared-DB integration, unchanged)
        ML service continues reading the same tables
```

**Key structural decision:** the ML service is *already* FastAPI. This migration is **not** "introduce Python" — it's "retire the Java service and let the two Python services either merge into one FastAPI app with routers, or remain two FastAPI deployables sharing one DB." Recommendation: keep them as **two separate deployables** (main backend + ML service) exactly as today, because:
- The ML service already has its own lifespan/training/APScheduler lifecycle that shouldn't compete with the main API's event loop under load.
- They currently share a DB, not an API boundary — merging them would be a bigger, riskier change than the migration itself asks for.
- Decoupled deploys mean the ML service's model retraining never blocks or restarts the transactional API.

---

## 3. System Design Overview

Layered structure, same shape as today, translated:

| Spring Boot layer | FastAPI equivalent |
|---|---|
| `@RestController` | FastAPI `APIRouter` per resource, same URL prefix |
| `@Service` | Plain Python service module/class, same method names where reasonable (aids diffing) |
| Spring Data JPA `Repository` | SQLAlchemy 2.0 async session + explicit queries (no repository-pattern requirement, but grouping by entity is fine) |
| JPA `@Entity` | SQLAlchemy `declarative_base()` model, 1:1 column mapping |
| DTOs (`dto/`) | Pydantic `BaseModel` schemas — request AND now response too (see §12, this is an *allowed* improvement) |
| `GlobalExceptionHandler` + `ApiException` | FastAPI exception handler registered on the app, one custom `ApiException(Exception)` carrying `message` + `status_code`, converted to the same JSON error shape |
| `JwtFilter` (`OncePerRequestFilter`) | FastAPI dependency (`Depends(get_current_user)`) or ASGI middleware — dependency is preferred, see MIGRATION_RULES |
| `SecurityConfig` `authorizeHttpRequests` allow-list | Per-route `Depends(require_role(...))` dependencies — **the full rule table in §9 must be reproduced rule-for-rule** |
| `RateLimitFilter` | ASGI middleware, same Redis-counter + in-memory fallback + 100 req/60s window keyed by JWT email |
| `@Scheduled` (PenaltyService, PayoutService) | APScheduler jobs (the ML service already uses APScheduler — same library, same conventions) |
| `SseEmitterRegistry` + Redis pub/sub | FastAPI `StreamingResponse`/`EventSourceResponse` + same Redis pub/sub channel naming |
| `@Async` EmailService | `BackgroundTasks` (FastAPI) or a small async task queue — must remain fire-and-forget, non-blocking |
| `DataInitializer implements CommandLineRunner` | FastAPI `lifespan` startup hook — must remain idempotent (existence-check before insert) |

---

## 4. Important Historical Design Decisions (carry these into FastAPI verbatim)

1. **Deterministic pickup OTP, not random-and-stored.** OTP = `HMAC-SHA256(orderId : current-minute-bucket)`, truncated to 4 digits, computed once at generation time and stored verbatim. Verification is a **literal string compare**, never a recompute. This was a deliberate choice to avoid a DB round-trip/uniqueness check at generation time. Do not "modernize" this into a random+DB-unique OTP — that changes the security/verification contract and breaks in-flight orders.
2. **Two independent OTP systems exist and must stay independent**: email-verification OTP (registration, DB-persisted, time-expiring) vs. pickup OTP (order collection, HMAC-derived, never expires by re-derivation). Don't let them share a table, a secret, or a service method.
3. **"No penalty until READY" rule** — an order that expires while still `PLACED`/`PREPARING` is marked `EXPIRED` with **zero penalty**, because the outlet never finished preparing the food. Only a `READY`-but-uncollected order is penalized. This is explicitly marked `CRITICAL FIX` in the current code, implying a prior incident where students were penalized unfairly for outlet-side delay. **This must have an explicit regression test in the FastAPI version.**
4. **Slot capacity uses optimistic locking with one retry**, not a pessimistic DB lock or an application-level mutex. `PickupSlot.version` increments on write; a version-conflict triggers exactly one retry in `OrderService`. SQLAlchemy's equivalent is a `version_id_col` mapper config — this must be wired, not silently dropped, or concurrent slot booking will overbook.
5. **Base64 document images are stored directly in Postgres `TEXT` columns**, not object storage — a deliberate (if unconventional) choice made during development specifically because object storage wasn't free-tier-friendly at the time. SQLAlchemy models for `OutletApplication`, `AdminApplication`, `VerificationReport` must use `Text`/unbounded string types for these columns, not `String(500)`, or uploads silently truncate.
6. **CORS uses `AllowedOriginPatterns("*")` + `allowCredentials(true)`** — a combination Spring only permits because credentials travel via header (`Authorization`), not cookies. FastAPI's CORS middleware must reproduce this: wildcard origin + `allow_credentials=True` + header-based auth only. If cookie-based auth is ever introduced later, this combination becomes invalid and must be revisited — flag, don't silently "fix" it now.
7. **The ML-service fallback contract is load-bearing.** Every ML call site (`MLClient` equivalent) must keep its typed fallback: 0.5 demand score, 0.5 no-show risk, 20-minute wait estimate, empty recommendation list — used whenever the ML service is disabled or times out (default 3000ms). The system's resilience story depends on these exact values remaining wired at every call site, not just "some try/except somewhere."
8. **Two structurally different demand-score computations** coexist on purpose: ML-service score (primary) and a rule-based windowed SQL fallback (`countDemandInWindow`/`getMaxDemandInWindow` — checks the same item's no-show history ±30 min around the same time-of-day over the prior 10 days). Both must be ported; they are not redundant, they're a resilience pair.
9. **Counter orders bypass slot capacity intentionally.** A manager creating a walk-in counter order can push `currentOrders` past `maxOrders` — capacity is a soft UX guardrail for students, not a hard invariant. Do not add a capacity check to counter-order creation "for consistency" — that would remove a feature managers rely on.
10. **`simulateOrderPayment` is a live, ungated payment bypass** in the current code (no profile/environment check found anywhere in the call chain — confirmed by direct inspection). It must be **explicitly, visibly gated** behind an environment flag (e.g. `ENVIRONMENT=development`) in the FastAPI version — this is a security fix that legitimately belongs in this migration, see §13.
11. **India-specific formats are hardcoded**, not configuration: INR currency strings, ₹ symbol in user-facing text, GST/FSSAI/IFSC-shaped format validation for outlet documents (format-only, no live government API call). Preserve as-is; do not "internationalize" as part of this migration — that's explicitly out of scope and would be scope creep on a already-large migration.
12. **Frontend already assumes a specific role-string shape**: `SUPERADMIN`, `ADMIN`, `MANAGER`, `STUDENT` (not the `docs/`-specified `SUPER_ADMIN`/`CAMPUS_ADMIN`/`CAFE_MANAGER`). JWT role claim, `ROLE_` prefix convention, and frontend's `role.replace("ROLE_","").toUpperCase()` normalization must all be preserved exactly.
13. **`GET /api/campuses/*` is `.authenticated()`, not role-restricted** — this is the *fixed* state of a prior bug where it was wrongly `hasRole("ADMIN")` and caused SuperAdmin 403s. Preserve the permissive rule; do not "tighten" it back.

---

## 5. Backend Responsibilities (unchanged scope)

Auth & registration · Users · Campuses · Outlet & Admin applications (onboarding + document verification) · Menu items · Pickup slots · Orders (student + counter) · Payments (Razorpay orders + verification + refunds) · Payouts (weekly aggregation + Razorpay X) · Razorpay webhook (inbound, HMAC-authenticated) · Penalties (scheduled expiry + demand-weighted charge) · Notifications · Outlet ratings · Roles · SSE order-status streaming · Rate limiting · ML client + fallback.

## 6. Frontend Assumptions (do not break these)

- Axios request interceptor reads the JWT from `localStorage["scf_auth"]` and attaches `Authorization: Bearer <token>` — the token shape and claim names must not change.
- Axios response interceptor does a hard `401` → clear storage → redirect to `/login`. Any endpoint that currently returns `401` on invalid/expired token must continue to do so (not `403`, not `440`, not a custom code).
- `ProtectedRoute` (has-token) wraps `RoleGuard` (role-in-list) — role strings arriving from `/api/auth/login` and `/api/users/me` must be the bare role name the frontend expects (`STUDENT`, not `ROLE_STUDENT`) — confirm exact current response shape per endpoint before changing anything.
- SSE consumption expects a specific event/message shape for order status pushes — the FastAPI SSE endpoint must emit byte-identical event payloads.
- Every JSON response shape that the frontend currently deserializes (raw JPA entity fields, camelCase) must be preserved field-for-field. Frontend code does **not** get touched as part of this migration — that is the entire point of doing this as a backend-only swap.

## 7. ML Service Assumptions

- Already FastAPI, already reads the same Postgres DB directly (shared-DB integration, not API composition) for training data.
- Main backend calls it over HTTP for inference only (`/recommendations`, `/wait-time`, `/slot-forecast`, `/no-show`, `/menu-analytics`, `/feedback`) — these HTTP contracts (paths, request/response JSON) are **frozen**; the migration must not touch `ml-service/` at all except where the *caller's* HTTP client is being rewritten in Python.
- The ML service has its own APScheduler for periodic retraining — independent lifecycle, do not merge into the main backend's scheduler.

## 8. Authentication Assumptions

- JWT: HS256, `sub=email`, `role` claim (bare role name, not `ROLE_`-prefixed inside the token — the `ROLE_` prefix is a Spring Security convention applied at the authority level, not in the token itself), `iat`, `exp` (default 24h, `JWT_EXPIRY_MS` env var).
- No refresh tokens, no revocation/blacklist — token is valid until natural expiry. This is a known, accepted limitation (see Technical Debt in the source analysis) — **not** something to silently fix during this migration; if you want to add refresh tokens, that is a separate, explicitly-approved follow-up project, not bundled into a "framework swap."
- JWT does **not** carry numeric user id or campus id — every authenticated request that needs "who is this" re-queries the user (and often the campus) by email. Preserve this pattern; do not "optimize" by stuffing more claims into the token without explicit sign-off (changes token size, changes what a leaked token exposes, and is not the migration's job).
- Two-step registration: `POST /register` (no token issued) → email OTP → `POST /verify-email` (token issued here) → `POST /login`.
- Password hashing: BCrypt in Java (`spring-security-crypto`). FastAPI equivalent: `passlib[bcrypt]` or `bcrypt` directly — **must produce hash-compatible verification against existing stored hashes** (BCrypt hash format is portable across languages; verify this explicitly with a real hash from the current DB before considering auth "done").

## 9. Full API / Role Authorization Matrix (must be reproduced exactly)

This is the literal, verified content of the current `SecurityConfig.authorizeHttpRequests` block. Every rule below is a contract the frontend depends on.

**Public (no auth):**
`/api/auth/**` (all) · `POST /api/admin-applications` · `POST /api/admin-applications/send-otp` · `POST /api/admin-applications/verify-otp` · `POST /api/outlet-applications` · `POST /api/payments/webhook/razorpay` · `POST /api/payments/order/**` · `GET /api/campuses`

**SUPERADMIN only:**
`POST /api/campuses` · `POST /api/campuses/*/deactivate` · `POST /api/campuses/*/reactivate` · `GET /api/admin-applications` · `GET /api/admin-applications/all` · `PATCH /api/admin-applications/*/approve` · `PATCH /api/admin-applications/*/reject` · `GET /api/outlet-applications/platform-pending` · `GET /api/payouts/all` · `GET /api/payouts/outlet/*` · `GET /api/payouts/failed` · `POST /api/payouts/*/retry` · `GET /api/payouts/summary/*` · `GET /api/outlets/all`

**SUPERADMIN or ADMIN:** `GET /api/orders`

**ADMIN only:**
`GET /api/outlet-applications/pending` · `GET /api/outlet-applications/all` · `GET /api/outlet-applications/*/verification-report` · `PATCH /api/outlet-applications/*/approve` · `PATCH /api/outlet-applications/*/reject` · `POST /api/outlets/*/suspend` · `POST /api/outlets/*/reactivate` · `DELETE /api/outlets/*` · `GET /api/payouts/campus` · `POST /api/penalties/*/waive`

**ADMIN or SUPERADMIN:** `GET /api/outlets/campus/*/all`

**MANAGER or ADMIN:** `GET /api/menu-items/all`

**MANAGER only:**
`GET /api/outlets/mine` · `POST /api/outlets/*/launch` · `POST /api/outlets/*/toggle` · `POST /api/menu-items` · `PATCH /api/menu-items/*` · `DELETE /api/menu-items/*` · `PATCH /api/orders/*/status` · `POST /api/orders/*/pickup` · `GET /api/orders/outlet/*` · `GET /api/payouts/my-outlet` · `PATCH /api/payouts/mine/bank-details` · `POST /api/slots` · `DELETE /api/slots/*` · `POST /api/manager/orders/counter` · `GET /api/manager/orders/ledger` · `GET /api/manager/orders/ledger/summary` · `PATCH /api/slots/*/adjust-count` · `PATCH /api/slots/*/capacity`

**STUDENT only:**
`POST /api/orders` · `GET /api/orders/student/*` · `POST /api/orders/*/cancel` · `POST /api/payments/initiate/order/*` · `POST /api/payments/verify/order` · `POST /api/payments/initiate/penalty/*` · `POST /api/payments/verify/penalty`

**Any authenticated user:**
`GET /api/users/me` · `PATCH /api/users/me/password` · `PATCH /api/users/me/profile` · `GET /api/campuses/*` · `GET /api/outlets/*` · `GET /api/outlets/campus/*` · `GET /api/menu-items` · `GET /api/orders/*` · `GET /api/payments/order/*` · `/api/notifications/**` · `/api/penalties/**` · `GET /api/slots`

**ADMIN or SUPERADMIN (specific overrides):**
`GET /api/users/campus/*` · `POST /api/payments/refund/order/*`

**SUPERADMIN:** `GET /api/users`

**Catch-all:** anything not listed above → `authenticated()`.

> Migration requirement: build this exact table as a single Python data structure (list of `(method, path_pattern, allowed_roles)` tuples) and drive route dependencies from it, or hand-wire each router's dependency and cross-check against this table line-by-line before sign-off. Either approach is fine; silently "reorganizing" the rules while porting is not — see MIGRATION_RULES §Business Logic Preservation.

## 10. Database Assumptions

- Postgres (Supabase-hosted). 16 entities: `User`, `Role`, `Campus`, `Outlet`, `MenuItem`, `PickupSlot`, `Order`, `OrderItem`, `Payment`, `OutletPayout`, `OutletRating`, `Notification`, `EmailOtpToken`, `AdminApplication`, `OutletApplication`, `VerificationReport`.
- Current dev profile uses `ddl-auto: update` (Hibernate auto-migrates schema from entity annotations); prod profile uses `validate`. **The FastAPI migration must introduce a real migration tool (Alembic)** — this is one of the explicitly-approved improvements (§16), since "no migration tool" is flagged as a real risk in the existing analysis, not a stylistic nit.
- **Shared-database integration with the ML service is load-bearing and fragile.** The ML service reads these same tables directly via raw SQL/SQLAlchemy, with **no schema-ownership boundary**. Any column rename, type change, or drop in the new SQLAlchemy models must be checked against `ml-service/database.py` and `ml-service/database_connector.py` before merging. This is the single highest-risk area of the entire migration — get explicit sign-off before any schema-shape change, even one that looks purely cosmetic (e.g., renaming `isActive` to `is_active` at the column level, not just the Python attribute level, would break the ML service silently).
- Status fields (`Order.status`, `Outlet.status`, `Payment.status`, `OutletPayout.status`) are plain strings today, validated by procedural `if`/`switch` logic, not DB-level enums. You may introduce Python-level enums (`str, Enum`) for developer safety **as long as the underlying column values written to Postgres are unchanged strings** — the ML service's raw SQL filters on these exact string values (`'READY'`, `'PICKED'`, etc.).
- `User.pendingPenaltyAmount` is a plain `double` — preserve as `Numeric`/`Float` consistently to avoid floating-point drift in money math; do not introduce a currency library or `Decimal`-everywhere refactor as part of this migration unless explicitly asked (scope control).

## 11. API Compatibility Requirements

- Every path, verb, and status code the frontend currently receives must be reproduced exactly. This includes error status codes (`ApiException`'s HTTP status must map 1:1).
- JSON field names: current responses are **raw JPA entity serialization** (camelCase, e.g. `pickupOtp`, `totalAmount`, `readyAt`). New Pydantic response models must alias to the same camelCase keys (`Config.alias_generator` / `populate_by_name`, or explicit `Field(alias=...)`) — do not switch to snake_case wire format even though that's more Pythonic; this is an explicit case where "improving" would break the frontend.
- `401` on invalid/missing/expired token, `403` on valid-token-wrong-role, `404` on missing resource, `400` on validation failure, `409`-or-equivalent on conflicts if that's what's currently returned — verify each controller's actual thrown status before assuming a "sensible default."
- The unauthenticated Razorpay webhook endpoint's HMAC verification contract (raw body + `X-Razorpay-Signature` header, HMAC-SHA256 hex compare) must be pixel-identical — Razorpay's signature is computed over the exact raw request body; any JSON re-serialization before verification (a common FastAPI/Pydantic trap — parsing to a model before checking the signature) will break every webhook.

## 12. Business Logic That Must Never Change

See §4 (OTP determinism, no-penalty-until-READY, optimistic locking, ML fallback contract, counter-order capacity bypass, Razorpay signature verification, JWT claim shape) — these are the load-bearing rules. Restated as a checklist in MIGRATION_RULES.md §Business Logic Preservation for enforcement.

## 13. Cross-Module Interactions (preserve the exact wiring)

- `createOrder` → synchronous ML call (wait-time) → synchronous ML call (no-show-risk, conditionally writes a notification) → two-stage save for COD OTP attachment → slot increment with retry. All in the request path today; you may parallelize the two ML calls (`asyncio.gather`) as a legitimate FastAPI-era improvement (async I/O is exactly what this framework is good at) — but the *order of business validation* (student penalty check → outlet check → daily cap → slot capacity → item validation) must not be reordered, since later checks assume earlier ones already passed.
- Status change (`updateOrderStatus`/`confirmPickup`/`cancelOrder`) → DB write → Redis SSE publish → Notification DB write, fired from one function, not transactional/saga-wrapped today. Preserve this "best effort" shape: if Redis publish fails, catch and continue (local-only SSE delivery), but the DB writes happen regardless. Do not silently upgrade this to a transactional outbox pattern without flagging it as an explicit, approved improvement (§16) — it changes failure-mode behavior.
- `PayoutService` uses raw HTTP (not an SDK) for Razorpay X because no Python SDK covers it either — expect to keep this as direct `httpx`/`requests` calls with Basic Auth, same as the Java `RestTemplate` approach.

## 14. Where docs/ Disagrees With Code (code wins)

`docs/database-schema.md` is stale/frozen-in-name-only: it specifies roles `SUPER_ADMIN`/`CAMPUS_ADMIN`/`CAFE_MANAGER`/`STUDENT` (code uses `SUPERADMIN`/`ADMIN`/`MANAGER`/`STUDENT`), an order flow with an `ACCEPTED` step that doesn't exist in code, and omits `Payment`, `OutletPayout`, `OutletRating`, `Notification`, `EmailOtpToken`, `AdminApplication`, `OutletApplication`, `VerificationReport` entirely. `docs/architecture.md` and `docs/roles-and-flows.md` are empty placeholders. **Do not consult `docs/` as a migration reference for anything** — every spec in this document was built from source code, verified by direct inspection.

## 15. Performance, Security, Deployment Considerations

**Performance:** async SQLAlchemy + async ML HTTP calls is a legitimate, expected win over synchronous Java blocking calls in the hot order-creation path — lean into `async def` end-to-end. Keep the ML timeout (3000ms) configurable, same default.

**Security:**
- Gate `simulateOrderPayment` behind an explicit environment check (§4.10) — this is a genuine vulnerability fix, do it.
- Preserve rate limiting exactly (100 req/60s per authenticated email, Redis + in-memory fallback) — and make its wiring **structural**, not a single easily-deleted line, as an approved improvement (currently one deleted line silently disables it platform-wide).
- Preserve HMAC verification for both Razorpay payment signatures and the payout webhook exactly.
- Keep all secrets in environment variables, same variable names where possible, to avoid re-touching deployment configs unnecessarily.

**Deployment:** the current setup assumes a Spring Boot JAR + a separate FastAPI ML service, both hitting one Postgres. Post-migration: two FastAPI ASGI apps (main + ML), same DB, same Redis. Confirm the hosting target (Uvicorn/Gunicorn workers, or a PaaS like Render/Railway that the student is already using for the free tier) before finalizing a Dockerfile/process model — do not assume; ask if not already known.

## 16. Things That Absolutely Must Remain Unchanged

Frontend code and its expected JSON shapes · JWT claim shape and role-string casing · deterministic OTP algorithm and secret derivation · order status transition rules · no-penalty-until-READY rule · optimistic-locking behavior on slots · counter-order capacity bypass · Razorpay/webhook signature verification logic · ML fallback constants and call sites · CORS wildcard+credentials combination · rate-limit thresholds and key (per-email) · India-specific hardcoded formats/currency · the two-OTP-systems separation · shared-DB column names/types the ML service depends on.

## 17. Things That May Safely Improve

Introduce Alembic migrations (replacing `ddl-auto`) · add response DTOs (Pydantic) instead of raw entity serialization · structure the rate-limit filter so it can't be silently disabled by one deleted line · gate the payment-simulation bypass behind an environment flag · parallelize the two independent ML calls in `createOrder` · add a typed exception hierarchy under the same `ApiException`-style base (still one JSON error shape on the wire) · add structured logging · add automated tests (there are currently none beyond a context-load smoke test) — **all of these must be flagged and approved per-module during migration, not silently bundled in**, per MIGRATION_RULES.

## 18. Hidden Constraints

- The ML service and new FastAPI backend will now both be Python — resist the temptation to merge them into one app "since they're the same language now." Keep them separate deployables (§2) unless the student explicitly wants a monorepo-single-service redesign as a *separate* decision, not a side effect of this migration.
- `spring-dotenv`'s `.env` loading convention should be mirrored with `python-dotenv` / `pydantic-settings`, same variable names, so the existing `.env.example` at repo root keeps working without edits.
- Free-tier constraints (test Razorpay keys, free Postgres/Redis tier, free SMTP relay) must keep working exactly as today — do not introduce a paid-tier-only SDK feature.

## 19. Manual Verification Checklist (run after each module, and again at the end)

- [ ] Every route in §9's matrix returns the correct status for: no token / wrong role / correct role.
- [ ] JWT issued by new `/login` is byte-shape-compatible with what `JwtFilter`/frontend expects (decode and diff claims against an old token).
- [ ] A password hashed by the old BCrypt implementation still verifies correctly against the new passlib/bcrypt verification.
- [ ] Pickup OTP generated for the same `orderId` + same minute bucket produces the identical 4-digit value in both implementations (run side-by-side with a fixed clock).
- [ ] Slot booking under concurrent load (script placing N simultaneous orders against a slot with capacity N-1) rejects exactly one order, not zero, not two.
- [ ] An order that expires while `PLACED` incurs no penalty; an order that expires while `READY` does.
- [ ] ML service unreachable → order creation still succeeds using fallback constants, and those constants match exactly (0.5 / 0.5 / 20 min / []).
- [ ] Razorpay webhook with a tampered body is rejected (403/400); a legitimate one is accepted.
- [ ] SSE stream delivers identical event shape/timing to the frontend's `OrderTrackingScreen`.
- [ ] CORS preflight from the actual frontend origin succeeds with credentials.
- [ ] `DataInitializer`-equivalent startup hook run twice in a row creates zero duplicate rows.
- [ ] ML service's raw queries against shared tables still return correct data after any schema touch-up (run its existing training/inference smoke path against the new schema).

## 20. Testing Strategy

Given there is currently **no automated test coverage** beyond a Spring context-load smoke test, this migration is the natural point to introduce `pytest` + `pytest-asyncio` + `httpx.AsyncClient` for endpoint tests, and a dedicated test Postgres schema/database (never the dev DB). Priority order for test-writing, highest business risk first: OTP generation/verification → order status transitions → penalty expiry logic (READY vs not-READY) → slot optimistic locking under concurrency → payment/webhook signature verification → the full authorization matrix from §9 (parametrized: role × route × expected status). Each module's migration prompt (see the Prompts document) specifies its own minimum test list.

## 21. Rollback Strategy

Migrate module-by-module behind a **route-level strangler pattern**: stand up the FastAPI app on a different port/path prefix first, and cut over the frontend's base URL per-module (or per-full-cutover, whichever the student prefers — see Prompts document intro) only after that module passes its manual verification checklist. Keep the Spring Boot backend deployable and untouched in a separate branch/tag until the very last module passes, so reverting is "point the frontend base URL back," not "revert code." Do not delete or archive the Spring Boot source until the FastAPI version has run in the intended production-equivalent environment for a real trial period.

## 22. Recommended Migration Order

1. Foundation: DB models (SQLAlchemy) + Alembic baseline + config/settings, no endpoints yet.
2. Auth (registration, email OTP, login, JWT, password hashing) — everything else depends on this.
3. Users, Campuses (low-risk, few business rules).
4. Outlet & Admin Applications (onboarding + document verification — moderate complexity, no financial risk).
5. Menu Items, Pickup Slots (introduces optimistic locking — first real concurrency-sensitive module).
6. Orders (highest complexity: OTP, slot capacity, status machine, ML calls) — do this only after Slots is solid.
7. Payments (Razorpay integration, signature verification, ties into Orders).
8. Notifications (mostly a side-effect consumer of Orders/Payments, low standalone risk).
9. ML integration wiring (the `MLClient` equivalent — the ML service itself is untouched, only its caller moves).
10. Background jobs (Penalty expiry, weekly Payouts via APScheduler).
11. Outlet Ratings, Roles (small, low-risk, can be done anytime — placed last only because they're low priority).
12. Final integration: rate limiting, CORS, full authorization-matrix audit, SSE, end-to-end smoke test against the real frontend.

## 23. Definition of Feature Parity

Feature parity means: every route in §9 exists at the same path/verb/role-gate, returns the same status codes and same JSON shape (field names, types, nullability) as the Spring Boot version, for every documented business rule in §4 and §12, verified against the checklist in §19 — not "the general idea is the same" and not "our own new test suite passes" in isolation from a side-by-side comparison against the old service's actual responses.
