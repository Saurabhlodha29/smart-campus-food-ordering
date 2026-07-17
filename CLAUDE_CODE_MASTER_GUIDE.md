# CLAUDE_CODE_MASTER_GUIDE.md
### How Claude Code should execute this migration
Read this alongside `MIGRATION_SPECIFICATION.md` (the what) and `MIGRATION_RULES.md` (the constraints). This document is the how.

---

## 1. Migration Philosophy

This is a **framework swap, not a rewrite.** The goal is a FastAPI backend that is behaviorally indistinguishable from the current Spring Boot backend to every external observer (the frontend, the ML service, Razorpay's webhook caller). Every decision should be evaluated against the question: *"would the frontend or ML service notice this change?"* If yes, it needs explicit approval before proceeding. If no, and it's a genuine code-quality improvement within the allowed list (spec §17), it's welcome.

Treat the Spring Boot source as the **executable specification**. When in doubt about behavior, the answer is "read the Java file," not "read the docs" and not "what would be idiomatic in FastAPI." Idiomatic-FastAPI-ness is a tiebreaker among options that all preserve behavior identically, never a reason to choose a behavior-changing option.

## 2. Expected Folder Structure

Mirror the current Spring package structure closely enough that a reviewer can find the Python equivalent of any Java file in seconds:

```
backend-fastapi/
  app/
    main.py                  # FastAPI app creation, router mounting, lifespan (DataInitializer equivalent)
    config.py                # pydantic-settings, mirrors application.yml env vars
    db.py                    # async engine/session setup
    models/                  # SQLAlchemy models, one file per entity (mirrors domain/)
    schemas/                 # Pydantic request/response models (mirrors dto/, but now covers responses too)
    routers/                 # APIRouter per resource (mirrors controller/)
    services/                # business logic (mirrors service/)
    security/                # jwt.py, deps.py (current-user + role-check dependencies), rate_limit.py
    exceptions.py            # ApiException + registered exception handler
    jobs/                    # APScheduler jobs (penalty expiry, weekly payouts)
    sse.py                   # Redis pub/sub + SSE streaming (mirrors SseEmitterRegistry)
  alembic/                   # migrations
  tests/                     # pytest, mirrors routers/ and services/ structure
  requirements.txt / pyproject.toml
```

Keep the ML service (`ml-service/`) completely untouched and separate — do not move it under `backend-fastapi/`.

## 3. Module Order

Follow `MIGRATION_SPECIFICATION.md` §22 exactly: Foundation → Auth → Users/Campuses → Applications → Menu/Slots → Orders → Payments → Notifications → ML integration → Background jobs → Ratings/Roles → Final integration. Do not skip ahead because a later module looks easy — later modules assume earlier ones are fully verified and approved.

## 4. Testing Process (per module)

1. Before writing any migration code, list the exact Java files being ported for this module and the exact endpoints from spec §9 this module owns.
2. Write the module's SQLAlchemy models + Pydantic schemas first, no logic yet.
3. Write the service layer, porting logic method-by-method, keeping method names similar to the Java source for easy diffing.
4. Write the router, wiring dependencies for auth/role-checks per spec §9.
5. Write tests **before** declaring the module done — at minimum, the role×route matrix slice and every business-rule checklist item from spec §19 that applies.
6. Run tests against a dedicated test DB. Run a manual smoke request against each new endpoint with a real token for each relevant role.
7. Only then write the module summary and stop for review (per MIGRATION_RULES §14).

## 5. Documentation Process

Each module gets a short markdown note (can live in `tests/` or a `migration-notes/` folder) containing: what Java files were the source of truth, what was ported verbatim, what (if anything) was flagged as a discrepancy or improvement candidate, and what still needs human decision. These notes are raw material the student will later fold into `INTERVIEW_NOTES.md` — write them assuming a future reader who wasn't in this session.

## 6. Review Process

At the end of every module: present a diff-style summary (old Java behavior → new Python behavior, called out anywhere they might differ even trivially), the test results, and an explicit request for approval to continue. Never bundle two modules' review into one sign-off — each module gets its own checkpoint, per MIGRATION_RULES §14.

## 7. Common Mistakes to Avoid

- **Reformatting business logic while translating it**, making it hard to verify against the Java original — port first, clean up only within the same module's explicit scope.
- **Assuming Python `float` behaves identically to Java `double`** in penalty/commission math without checking — verify with the same test inputs against both implementations where the old service is still runnable.
- **Parsing the Razorpay webhook body into a Pydantic model before verifying its HMAC signature** — this changes the exact bytes being signed-over and will break verification. Verify against the raw body first, parse second.
- **Dropping the optimistic-lock retry-once behavior** on slot booking because "SQLAlchemy handles versioning automatically" — the *retry* behavior (exactly one retry, not infinite, not zero) is application logic that must be explicitly reimplemented.
- **Snake-casing response JSON** because it's more Pythonic — breaks the frontend silently (no crash, just wrong/missing fields it can't see because it's still reading `camelCase` keys that no longer exist).
- **"Fixing" the no-penalty-until-READY rule's edge cases** without being told to — this exact rule has a documented prior-incident history; treat any temptation to touch it as a stop condition, not a cleanup opportunity.
- **Merging the ML service into the new FastAPI backend** because they're now both Python — explicitly out of scope, see spec §18.
- **Silently changing the rate-limit window/threshold** while restructuring the filter into "proper" middleware — the *behavior* (100/60s, per-JWT-email, Redis + in-memory fallback) must be identical even as the *mechanism* for wiring it becomes more robust (spec §17 approves fixing the fragile wiring, not changing the numbers).

## 8. How to Verify Feature Parity

For each module, run the same sequence of requests against both the still-running Spring Boot service and the new FastAPI service (using a shared test dataset, ideally seeded identically in both), and diff:
1. Response status code.
2. Response JSON (structurally — same keys, same types, same nullability — not necessarily identical dynamic values like timestamps/generated IDs).
3. Side effects: query the DB directly after each call and diff the resulting rows (same columns changed, same values, same status transitions).
4. For scheduled jobs (penalty expiry, payouts): run both implementations against an identical pre-seeded "stale order" dataset and diff the resulting DB state and any outbound calls (mock Razorpay/SMTP in both).

This side-by-side comparison, not "the new tests I wrote pass," is the actual definition of feature parity per spec §23. Keep the old service runnable (even just locally) for exactly this purpose until the final module is signed off.
