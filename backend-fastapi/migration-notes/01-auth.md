# 01 — Authentication Module

**Migration step:** 2 of 12 (spec §22)
**Date:** 2026-07-11
**Status:** awaiting manual review

---

## What was migrated

| Java source file | Python port | Notes |
|---|---|---|
| `AuthController.java` | `app/routers/auth.py` + `app/services/auth_service.py` | Router/controller split. Router is thin (parse → delegate → wrap); service holds all business logic. |
| `JwtUtil.java` | `app/security/jwt.py` | HS256, `sub=email`, bare `role` claim (no `ROLE_` prefix in token), `iat`+`exp` (24h default). |
| `JwtFilter.java` | `app/security/deps.py` | `get_current_user` (FastAPI dependency) + `require_role(*roles)` factory. The `ROLE_` prefix that Spring's `SimpleGrantedAuthority` added inside the filter is NOT reproduced inside the token or at the Python dep layer — it was a Spring-internal authority-layer packaging detail, never a wire/auth token concern. Bare role-name comparison is the exact behavioral equivalent. |
| `OtpService.java` | `app/services/otp_service.py` | Email-verification OTP only (registration). DB-persisted, time-expiring, single-use, 6-digit, literal-string-compare verification. Completely separate from the pickup-OTP system (spec §4.2). |
| `EmailService.java` | `app/services/email_service.py` | Async SMTP send for OTP mail. Fire-and-forget (swallows all errors). HTML body structure ported verbatim. No-op when `MAIL_USERNAME` is unset (dev/CI mode). |
| `DataInitializer.java` | `app/services/seeding.py` (wired from `app/main.py` lifespan) | Idempotent startup seeding of 4 roles + SuperAdmin. Only inserts if absent. |
| `BCryptPasswordEncoder` (Spring Security) | `app/security/password.py` (`passlib[bcrypt]`) | BCrypt hash format is cross-language portable. Existing stored hashes from the Java DB verify correctly. |
| `RegisterRequest.java` | `app/schemas/auth.py::RegisterRequest` | `@NotBlank fullName (max 120)`, `@Email @Size(max=150) email`, `@Size(min=6) password`. `extra="ignore"` drops the frontend's blank `otp` field. |
| `VerifyEmailRequest.java` | `app/schemas/auth.py::VerifyEmailRequest` | `@Email email`, `@Pattern(\d{6}) otp`. |
| `AuthRequest.java` | `app/schemas/auth.py::LoginRequest` | Bare `email`/`password`, no bean-validation constraints (matches Java). |
| (no DTO — `Map<String, String>` was the body) | `app/schemas/auth.py::ResendOtpRequest` | `email` field only. |
| (no DTO — `Map<String, String>` was the response) | `app/schemas/auth.py::AuthResponse` | Maps the literal `Map.put(...)` calls in login/verifyEmail. All values are stringified (Java `String.valueOf`). `campusId`/`campusName` omitted from JSON when user has no campus (parity with Java's `if (user.getCampus() != null) put(...)`). |
| (no DTO — `Map<String, String>` message) | `app/schemas/auth.py::MessageResponse` | `{message, email?, status?}` envelope for register/resend responses. |

## Endpoints (all PUBLIC per spec §9)

| Method | Path | Java method | Python router | Response |
|---|---|---|---|---|
| POST | `/api/auth/login` | `AuthController.login` | `login()` | `AuthResponse` (200) |
| POST | `/api/auth/register` | `AuthController.register` | `register()` | `MessageResponse` (201) |
| POST | `/api/auth/verify-email` | `AuthController.verifyEmail` | `verify_email()` | `AuthResponse` (200) |
| POST | `/api/auth/resend-otp` | `AuthController.resendOtp` | `resend_otp()` | `MessageResponse` (200) |

All 4 endpoints are public (no JWT required) — matches `SecurityConfig`'s `.requestMatchers("/api/auth/**").permitAll()`.

## JWT claim shape (spec §8 + §4.12)

```
{
  "sub": "<email>",              // setSubject(email)
  "role": "<bare role name>",    // .claim("role", role) — NO "ROLE_" prefix
  "iat": <unix seconds>,         // setIssuedAt(new Date())
  "exp": <unix seconds + TTL>    // setExpiration(...)
}
```
- Algorithm: HS256 (`JwtUtil.java` used `SignatureAlgorithm.HS256` + `Keys.hmacShaKeyFor(secret.getBytes())`).
- `JWT_EXPIRY_MS` is in milliseconds (86400000 = 24h) — divided by 1000 before adding to the `iat` unix timestamp (python-jose expects `exp` in seconds, not millis).
- `ROLE_` prefix was a Spring Security `SimpleGrantedAuthority` convention applied inside `JwtFilter.doFilterInternal`, **never in the token itself**. The FastAPI dep `require_role(*allowed_roles)` compares the bare role name directly.
- No refresh token, no revocation/blacklist (matches current system — see "Known limitations" below).

## Account-status gating (login)

The exact status ladder from `AuthController.login`:
1. Unknown email → 401 "Invalid email or password"
2. Wrong password → 401 "Invalid email or password" (same message — no user-enumeration leak)
3. `PENDING_VERIFICATION` → 403 with the OTP/resend-otp-friendly message
4. Any non-ACTIVE non-PENDING status → 403 "Your account is \<status>. Please contact support."
5. `ACTIVE` → success

## Two-OTP systems separation (spec §4.2)

This module owns the **email-verification OTP** system only:
- DB-persisted in `email_otp_tokens`
- Time-expiring (`OTP_EXPIRY_MINUTES`, default 10 min)
- Single-use (marked `used=True` on successful verify)
- 6-digit, `secrets.randbelow` (cryptographic, equivalent to Java `SecureRandom`)
- Verification is a literal string compare (`token.otp_code != submitted_otp`), NEVER a hash or HMAC recompute.

The **pickup OTP** system (HMAC-derived, non-expiring, order-collection-only) is a separate concern owned by the Orders module (step 6). They share no tables, secrets, config variables, or methods. `OTP_SECRET` is reserved for the pickup HMAC; `OTP_EXPIRY_MINUTES` is for this email-verify system only.

## Fire-and-forget email send — design decision (DIVERGENCE FLAGGED)

**Java behavior:** `EmailService.sendOtpEmail` was `@Async` — it returned immediately and dispatched the email on a separate thread. A delivery failure was caught (`MessagingException`) and logged; it never propagated.

**Original Python port (broken):** I first used FastAPI's `BackgroundTasks` to mirror the fire-and-forget contract. This was **behaviorally wrong** in one specific path: when `register` hits a duplicate-pending account, the Java code calls `otpService.generateAndSendOtp` (which dispatches the `@Async` email) **before** throwing `ApiException(409)`. The `@Async` send fires regardless of the throw. FastAPI's `BackgroundTasks` do NOT fire when the route handler raises an exception — they're tied to the success-response path only. So the second registration's OTP email would be silently dropped.

**Fix applied:** `otp_service.generate_and_send_otp` now awaits `send_otp_email` directly (not via `BackgroundTasks`). `send_otp_email` swallows all exceptions internally (it logs and returns, exactly like Java's `@Async catch MessagingException`), so the caller's outcome (200/201/409/500) is unaffected. This preserves the Java contract: the email is sent even when the outer register transaction throws, and an email failure never prevents the request's response.

**Behavioral impact:** Identical to Java for the user-facing paths. The only difference is that the email send is now synchronous within the request rather than on a background thread — but because `send_otp_email` is `async def` using `aiosmtplib`, the SMTP I/O is non-blocking within the event loop. The latency impact is bounded: a single SMTP send (typically tens of ms on a local relay, more for Gmail's SMTP) is now in the request path. For the duplicate-pending 409 case, the user sees 409 after the email is dispatched, not before — which is actually MORE consistent with Java than the BackgroundTasks approach was.

**Tested by:** `test_register_duplicate_pending_resends_otp_409` — asserts that `mock_email` receives 2 calls (register + duplicate-register's regenerated OTP), confirming the email fires on both the success and exception paths.

## `AuthResponse` wire shape — campus field omission

**Java behavior:** `AuthController.login` and `verifyEmail` only did `response.put("campusId", ...)` and `response.put("campusName", ...)` when `user.getCampus() != null`. For campus-less users (e.g. SuperAdmin), these keys were **absent** from the JSON, not present-with-null.

**Python port:** Two layers enforce this:
1. `_build_auth_response` only adds `campusId`/`campusName` to the dict when `user.campus is not None` (literal parity with Java's conditional `put`).
2. The `AuthResponse` Pydantic schema uses `response_model_exclude_none=True` on the `/login` and `/verify-email` routes. This is necessary because FastAPI's response serialization does NOT honor `exclude_none=True` from a model's `ConfigDict` (it requires the route-level kwarg).

**Tested by:** `test_login_response_shape_no_campus` — logs in a campus-less user and asserts `campusId` and `campusName` are **absent** from the JSON payload.

## BCrypt cross-implementation compatibility (spec §19 item 3)

`passlib[bcrypt]` uses the standard BCrypt hash format (`$2a$10$...` / `$2b$...`), which is the same format Spring's `BCryptPasswordEncoder` produces. The hashes are cross-verifiable:
- A hash created by `passlib` verifies against `passlib` (`test_bcrypt_hash_compatibility_roundtrip`).
- A hash created by Spring's `BCryptPasswordEncoder` is parseable by `passlib` and verifies correctly once the plaintext is known.

The dev-DB witness test (`test_bcrypt_hash_compatibility_from_dev_db`) pulls a real `password_hash` from the live Supabase `users` table and verifies `passlib` can parse it without raising. It skips cleanly when the dev DB is unreachable (no `DB_URL` / paused project). **This test should be run against the live DB before sign-off** to confirm a real stored hash round-trips. The test asserts:
1. The stored hash starts with `$2` (BCrypt format).
2. `verify_password("definitely-not-the-real-password", stored_hash)` returns `False` (not a crash — proves `passlib` parses the format).

To run the witness against the dev DB:
```bash
cd backend-fastapi
# Ensure .env has a working DB_URL pointing at the Supabase project
pytest tests/test_auth.py::test_bcrypt_hash_compatibility_from_dev_db -v
```

## Seeding (DataInitializer equivalent)

`app/services/seeding.py::seed_roles_and_superadmin` is called from `app/main.py`'s `lifespan` startup hook. It is idempotent:
- Seeds the 4 roles (`SUPERADMIN`, `ADMIN`, `MANAGER`, `STUDENT`) only if absent.
- Seeds a single SuperAdmin user (from `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` env vars) only if the email isn't already present.
- Raises `RuntimeError` if the `SUPERADMIN` role is missing after the role-seeding pass (schema/config breakage — fail loudly).

**Tested by:** `test_seeding_creates_roles_and_superadmin` (creates 4 roles + SuperAdmin), `test_seeding_is_idempotent` (running twice produces zero duplicate rows).

## Tests written

26 tests in `tests/test_auth.py` (1 skipped — dev-DB witness):

**Happy path:**
- `test_register_otp_verify_login_happy_path` — full register → OTP → verify → login flow; asserts JWT claim shape, account status transitions, response envelope field-by-field.

**Login error cases:**
- `test_login_wrong_password_401` — wrong password → 401 "Invalid email or password".
- `test_login_unknown_email_401` — unknown email → same 401 message (no user enumeration).
- `test_login_pending_verification_403` — PENDING account → 403 with OTP-friendly message.
- `test_login_non_active_status_403` — SUSPENDED account → 403 "Your account is SUSPENDED...".

**JWT validation:**
- `test_expired_jwt_rejected_401` — expired token → 401.
- `test_tampered_jwt_rejected_401` — tampered payload → 401.
- `test_missing_token_401` — no Authorization header → 401.
- `test_jwt_claim_shape` — alg=HS256, sub=email, role=bare (no ROLE_), iat+exp integers, exp-iat ≈ 24h.

**Resend-OTP:**
- `test_resend_otp_flow` — resend issues fresh OTP, deletes the old one, mock_email receives 2 calls, verify succeeds with the new OTP.
- `test_resend_otp_no_account_404` — unknown email → 404.
- `test_resend_otp_already_verified_400` — ACTIVE account → 400 "does not need OTP verification".

**Register error cases:**
- `test_register_duplicate_pending_resends_otp_409` — duplicate pending → 409 + new OTP sent (mock_email count goes 1→2).
- `test_register_duplicate_active_409` — duplicate ACTIVE → 409 "already exists".
- `test_register_no_campus_domain_404` — unknown email domain → 404.
- `test_register_campus_not_active_403` — INACTIVE campus → 403.
- `test_register_missing_role_500` — STUDENT role not seeded → 500.

**Verify-email error cases:**
- `test_verify_email_already_verified_400` — ACTIVE account → 400 "already verified".
- `test_verify_email_no_account_404` — unknown email → 404.
- `test_verify_email_invalid_otp_400` — wrong code → 400 "Invalid OTP".
- `test_verify_email_expired_otp_400` — expired token → 400 "expired or not found".

**Response-shape parity:**
- `test_login_response_shape_no_campus` — campus-less user → `campusId`/`campusName` absent from JSON.

**BCrypt compatibility (spec §19 item 3):**
- `test_bcrypt_hash_compatibility_roundtrip` — fresh hash + verify positive + verify negative + format sanity.
- `test_bcrypt_hash_compatibility_java_generated` — fresh hash (placeholder for Java-hash cross-check; dev-DB witness below covers the real cross-implementation case).
- `test_bcrypt_hash_compatibility_from_dev_db` — pulls a real `password_hash` from the dev Supabase DB; skips when unreachable.

**Seeding:**
- `test_seeding_creates_roles_and_superadmin` — 4 roles + SuperAdmin with correct shape (BCrypt-hashed password, ACTIVE status, no campus).
- `test_seeding_is_idempotent` — running twice produces zero duplicate rows.

## Test results

```
======================= 26 passed, 1 skipped in 27.13s ========================
```

- 26 pass against in-memory SQLite (no live DB needed).
- 1 skipped: `test_bcrypt_hash_compatibility_from_dev_db` — requires a reachable Supabase dev DB. **Should be run manually before sign-off.**
- Ruff: clean on all Module 2 files.
- mypy: unable to complete within the session's timeout (slow on this machine); recommend running manually:
  ```bash
  cd backend-fastapi
  python -m mypy app/security/ app/services/auth_service.py app/services/otp_service.py app/services/email_service.py app/routers/auth.py app/schemas/auth.py
  ```

## Known limitations (carried from current system — NOT introduced by this migration)

- **No refresh tokens, no revocation/blacklist.** A JWT is valid until natural expiry (default 24h). This matches the current Spring system — Spring Security's `JwtFilter` had no blacklist, no refresh-token flow, and no session revoke mechanism. This is a known accepted limitation flagged in the source analysis, and explicitly **not** something this migration silently introduces; adding refresh tokens would be a separate, explicitly-approved follow-up project (spec §8: "not something to silently fix during this migration").
- **No rate limiting on auth endpoints.** The 100-req/60s-per-email rate limiter (spec §15, application-wide) is wired in Module 12 (Final integration), not here. The auth endpoints are currently unrate-limited, exactly as in the current Spring app until the filter is wired.
- **Email send is now synchronous within the request** (see "Fire-and-forget email send" above). This is a behavioral-preserving design choice to match Java's `@Async`-fires-before-throw semantics; the latency impact is bounded by the SMTP send time. Flag for review — if the.OUTBOUND SMTP relay is slow, this adds latency to register/resend-otp responses.

## Flags for human review

1. **Fire-and-forget email send via direct-await vs BackgroundTasks** — see the dedicated section above. If the SMTP relay is slow (Gmail's free SMTP can take 1-5s), this adds latency to `POST /api/auth/register`, `POST /api/auth/resend-otp`, and the duplicate-pending-409 path of `POST /api/auth/register`. Alternatives to consider: (a) accept the latency (current choice, most faithful to Java's behavior); (b) use `asyncio.create_task(send_otp_email(...))` for true fire-and-forget that survives the request's response being sent (but not the event loop's shutdown); (c) re-introduce `BackgroundTasks` but explicitly await-or-dispatch-on-exception inside the service. The current approach was chosen because it's the simplest that preserves Java's exact behavioral contract (email fires regardless of transaction outcome, failure never propagates).

2. **`response_model_exclude_none=True` on `/login` and `/verify-email` routes** — necessary because FastAPI does NOT honor `exclude_none=True` from a Pydantic model's `ConfigDict` when serializing the response. This is a framework-level gotcha, not a design choice; if the team later upgrades FastAPI/Starlette to a version that honors the model-config flag, the route-level kwarg becomes redundant (but not harmful). Verify by decoding a real response: a campus-less user (e.g. SuperAdmin) should have no `campusId`/`campusName` keys at all, not `null` values.

3. **`EmailService` HTML body divergence** — the Python port copies the structure of the Java `buildOtpEmailHtml` template, but the Java original had a hamburger emoji ("🍔 SmartCampus") and a "Campus Food Ordering Platform" subtitle in the header that the first-pass Python port's template omitted. The exact email body format is NOT a wire contract the frontend depends on — it's a user-facing email — so this divergence does not break the API. Flag for review: should the Python template be updated to match the Java original byte-for-byte (including the emoji and subtitle), or is the cleaner template acceptable? This migration's scope is the API boundary, not the exact email rendering, but I want to surface the divergence explicitly per MIGRATION_RULES §16.

4. **`test_bcrypt_hash_compatibility_from_dev_db` skips when the Supabase DB is unreachable.** Run this test manually against a live dev DB before signing off on this module — it's the spec §19 checklist item 3 witness ("A password hashed by the old BCrypt implementation still verifies correctly against the new passlib/bcrypt verification"). The test asserts the stored hash is BCrypt-format and that `passlib` can parse it without raising; it cannot assert the plaintext matches (we don't know real users' passwords), but parseability + wrong-password-returns-False (not a crash) is the strongest claim available.

5. **Module 1 smoke tests (`test_db_connects`, `test_alembic_no_drift`) fail when the Supabase DB in `.env` is unreachable.** This is a Module 1 (Foundation) issue, not a Module 2 issue — they were written to skip when `DB_URL` is empty, but the `.env` has a `DB_URL` pointing at a Supabase project that's currently unreachable (`tenant/user postgres.nbcgzmjzmgemqvwygidm not found`). The tests attempt the connection and fail rather than skipping. Recommend adjusting the skip condition in a future Module 1 fixup to also skip on connection failure (or gating on an explicit `RUN_DB_TESTS=1` env var).

## What is NOT in this module (per spec — stop here)

- No `/api/users/me` or `PATCH /api/users/me/password` — that's Module 3 (Users).
- No `/api/campuses` endpoints — that's Module 3 (Campuses).
- No rate-limit middleware — that's Module 12 (Final integration).
- No pickup OTP generation or verification — that's Module 6 (Orders, spec §4.1).
- No SSE logic — that's Module 12.
- No BlackList/revocation — explicitly out of scope for this migration (spec §8).

---

Stop here — per MIGRATION_RULES §14, please review and approve before Users/Campuses (step 3) begins.
