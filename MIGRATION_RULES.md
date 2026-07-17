# MIGRATION_RULES.md
### Binding rules for every Claude Code migration session on this project
**This document is a constitution, not a suggestion list.** Attach it in full to every Claude Code session working on this migration. It must be read alongside `MIGRATION_SPECIFICATION.md` before any code is written. If a rule here and an instruction in a specific prompt ever conflict, **stop and ask** — do not silently pick one.

---

## 1. API Compatibility

- Every endpoint must match the Spring Boot version's path, HTTP verb, required role(s), and status codes exactly, as enumerated in `MIGRATION_SPECIFICATION.md` §9. No renaming paths "for REST purity." No changing `PATCH` to `PUT` because it "should" be idempotent. No collapsing two endpoints into one with a query param.
- Response JSON keys stay camelCase, matching current entity serialization, even though Pydantic defaults favor snake_case. Use field aliases. Verify against an actual captured response from the running Spring Boot service where any doubt exists — do not guess a field name from the entity's Java attribute name alone, since `@JsonProperty` overrides exist in places.
- Error response shape (whatever `GlobalExceptionHandler` currently emits — message + status code) must be reproduced exactly, including field names in the error body.
- Never introduce a new required request field, a new required response field, or a stricter validation rule than currently exists, without flagging it explicitly and getting sign-off. The frontend was not rewritten for this migration and cannot absorb API surface changes silently.

## 2. Business Logic Preservation

- Every rule listed in `MIGRATION_SPECIFICATION.md` §4 and §12 is **non-negotiable** unless the human explicitly approves a change in writing, in that exact session.
- If you find a business rule in the Java code that isn't mentioned in the spec, **do not assume it's a bug and "fix" it during translation.** Port it faithfully, then separately flag it as a discovered discrepancy for human review. Silent divergence between old and new behavior is the single worst outcome of this migration.
- Numeric/financial logic (penalty calculation, commission split, refund amounts) must be ported with the exact same formula, rounding behavior, and operator precedence. Floating-point vs. decimal behavior differences between Java `double` and Python `float` must be explicitly checked, not assumed equivalent.
- Order-of-operations in multi-step service methods (see spec §13) must be preserved even when reordering would look cleaner in Python — later steps may depend on earlier steps having already thrown.

## 3. Database Compatibility

- Column names, types, nullability, defaults, and uniqueness constraints must match the current schema exactly unless a change is explicitly called out and approved (e.g., introducing Alembic is approved; renaming a column is not, by default).
- Never let an ORM "auto-migrate" silently alter a live schema. All schema changes go through an explicit, reviewed Alembic migration file — no `Base.metadata.create_all()` against a database that already has data, ever.
- Before touching any table also read by `ml-service/database.py` or `ml-service/database_connector.py`, check what that file expects. If a touch-up requires a shape change (rename/type/drop), stop and flag it as a two-service coordination point rather than making the change unilaterally.
- Preserve every foreign key and cascade behavior currently enforced at the DB or ORM level.

## 4. Frontend Compatibility

- The frontend (`frontend/`) is out of scope for this migration and must not be edited. If a discovered incompatibility seems to require a frontend change, stop and flag it — do not "fix it on both sides" without explicit approval, since the frontend was deliberately kept out of this migration's blast radius.
- SSE event payload shape and CORS behavior (§ spec 6, 15) must be verified against actual frontend consumption code, not assumed from the backend side alone.

## 5. ML Service Compatibility

- `ml-service/` is not touched by this migration except insofar as the main backend's HTTP client code calling into it is being rewritten. Its own routes, models, and DB access patterns are frozen.
- Any main-backend schema change must be checked against ML service DB access before being applied (see §3).
- The ML fallback contract (spec §4.7) must be implemented at every call site that currently has it — do a literal line-by-line audit against the current `MLClient` before declaring a module done.

## 6. Code Quality

- Type-hint everything. `mypy`-clean is the bar, not merely "runs."
- No bare `except:` — catch specific exceptions, and log what was caught.
- No business logic inside route handlers — route handlers parse/validate input, call a service function, return a response. Keep the layered shape from the spec.
- No global mutable state except where the original Java code deliberately used it (e.g., the in-memory rate-limit fallback map) — and even then, make the Python equivalent explicit and documented, not an implicit module-level dict discovered by accident.

## 7. FastAPI Best Practices

- Use `APIRouter` per resource, mounted with the exact prefix matching the current controller's `@RequestMapping` base path.
- Use dependency injection (`Depends`) for current-user extraction and role checks — do not hand-roll auth checks inside each handler.
- Use `async def` for every handler and every DB call (async SQLAlchemy session) — this is a legitimate performance improvement over the Java blocking model, and the point of doing this migration in FastAPI at all.
- Return Pydantic response models, not raw dicts or raw ORM objects, from every handler.
- Register one exception handler translating the custom `ApiException` (and Pydantic `ValidationError`) into the exact current error JSON shape.

## 8. SQLAlchemy Best Practices

- SQLAlchemy 2.0 style (`Mapped[...]`, `mapped_column(...)`), async engine + async session, not the legacy 1.x query API.
- One model file per entity or a small number of grouped files mirroring the current `domain/` package — don't invent a wildly different file organization that makes side-by-side diffing against the Java source harder for review.
- Reproduce `@Version`-based optimistic locking using SQLAlchemy's `version_id_col` — do not reimplement it by hand with a manual `WHERE version = :v` unless there's a specific reason `version_id_col` doesn't fit, and flag that reason if so.
- All relationships (`ManyToOne`, `OneToMany`) mapped explicitly with matching cascade/lazy-load behavior equivalents — check whether the Java code relies on lazy-loading a relation inside a serialization path (it might, since entities are directly serialized in several places) before assuming eager loading is a safe default everywhere.

## 9. Pydantic Best Practices

- Separate `Create`/`Update`/`Response` schemas per resource, not one shared schema abused for all three directions.
- Use `Field(alias=...)` (or a shared camelCase alias generator with `populate_by_name=True`) to keep wire format camelCase while keeping Python attributes snake_case internally.
- Validate at the Pydantic layer whatever Spring's `@Valid`/bean-validation annotations currently validate — check each DTO in `dto/` for annotations like `@NotNull`, `@Email`, `@Size` before assuming "no explicit validation" means "no validation needed."

## 10. Documentation Requirements

- Every migrated module ships with: a short module README section (what it does, what it preserves, what changed and why), and inline docstrings on every non-trivial function explaining *why*, not just *what*, especially for anything ported from a Java comment marked `CRITICAL`, `FIXED`, or `NOTE`.
- Any discovered discrepancy between code and `docs/` (per spec §14), or any newly-discovered business rule not previously documented, gets written down in the module's migration notes for `INTERVIEW_NOTES.md` to later absorb.

## 11. Testing Requirements

- Every migrated module ships with `pytest` tests covering at minimum: the manual verification checklist items from `MIGRATION_SPECIFICATION.md` §19 that apply to that module, and the full role×route matrix slice for that module's endpoints.
- Concurrency-sensitive logic (slot booking, penalty expiry) gets a test that actually exercises concurrent access, not just sequential calls that happen to pass.
- Tests run against a dedicated test database, never the development or production database.

## 12. Definition of Done (per module)

A module is **not done** until all of the following are true:
1. Every endpoint listed for that module in the spec's §9 matrix exists, with correct role gating, verified against a real request (not just "the code looks right").
2. Every business rule for that module listed in spec §4/§12 has an explicit passing test.
3. No schema change was made without an Alembic migration and, if shared with the ML service, explicit sign-off.
4. `mypy` and the project's linter run clean on the new module's files.
5. A short module summary has been written (per §10) explaining what was ported, what (if anything) intentionally changed, and what was flagged for human review.
6. The human has manually reviewed and approved before the next module begins.

## 13. Stop Conditions — when Claude Code must halt and ask, not proceed

- Any business rule found in Java source that contradicts or isn't covered by `MIGRATION_SPECIFICATION.md`.
- Any required schema change touching a table `ml-service/` also reads.
- Any ambiguity in what status code/error shape a given failure path should return.
- Any place where reproducing current behavior would mean reproducing a real security bug (e.g., the ungated `simulateOrderPayment`) — flag it, propose the minimal fix from spec §16, and wait for approval before implementing even that fix.
- Any test that fails and the cause isn't immediately obvious — do not comment out a failing test to "keep moving."
- Reaching the end of a module's prompt scope — always stop for review before starting the next module, even if it feels like natural momentum to continue.

## 14. Approval Workflow

Each module prompt (see the Prompts document) ends with an explicit "stop here" instruction. Claude Code presents: what was migrated, what tests were written and their results, what (if anything) was flagged per §13, and what it needs from the human before continuing. The human reviews, then either approves proceeding to the next module or requests changes. No module's code should be treated as final until this explicit approval happens — "it compiled and the happy path worked" is not approval.

## 15. Handling Uncertainty

- If the exact current behavior of some Java code is genuinely ambiguous from reading it (e.g., an edge case in status transition logic that isn't covered by an existing test), say so explicitly and propose the most conservative reading (the one closest to current observed behavior), rather than picking whichever reading is easiest to implement.
- Never invent a business rule that "seems reasonable" to fill a gap — surface the gap instead.

## 16. Error Reporting

- When something can't be completed as specified, report *why* precisely (missing information, a genuine contradiction in the spec, a technical blocker) rather than silently substituting a different approach and mentioning it only in passing.
- Any deviation from the spec, however small, gets called out explicitly in the module summary — never buried in a code comment only.

## 17. Migration Discipline

- One module at a time, in the order specified in `MIGRATION_SPECIFICATION.md` §22, unless the human explicitly reorders.
- No refactoring or "cleanup" of code outside the current module's scope, even if you notice something else that looks wrong — note it, don't fix it, unless it's a stop-condition-level issue.
- No dependency upgrades, package additions, or tooling changes beyond what's needed for the current module, without calling it out first.
- Every session begins by re-reading `MIGRATION_SPECIFICATION.md` and this file in full — do not rely on a summary of them carried over from a previous session's context.
