"""Application service — business logic for the onboarding endpoints.

Source of truth: ``AdminApplicationController.java`` + ``OutletApplicationController.java``
(Spring Boot). This module is the pure-business-logic layer; routers parse +
validate Pydantic request models, call these functions, and wrap the returned
dicts in Pydantic response models.

WHAT'S PRESERVED FAITHFULLY
---------------------------
- The 3-attempt cap (MAX_ATTEMPTS = 3) — enforced on submit, hard stop with
  403 on the (N+1)th attempt for that email once N applications exist.
- The pending-duplicate check (one PENDING application per email at a time).
- Public submission (no JWT) for both admin and outlet applications — they
  predate any account being created.
- SUPERADMIN-only review/approve/reject for admin applications.
- ADMIN-only review/approve/reject for outlet applications, **scoped to the
  admin's own campus** — enforced both in resolve_admin (404 if no campus)
  and in the per-application check (403 if app's campus != admin's campus).
- Approve creates the downstream entities atomically:
    * admin-app approve  → Campus (ACTIVE) + User (ADMIN role)
    * outlet-app approve → User (MANAGER role) + Outlet (PENDING_LAUNCH)
  + writes a Notification row to the new account. Bank details from the
  application are pre-filled onto the outlet, matching the Java setter calls.
- The verification-failed warning in the outlet approve response (Java
  conditionally added ``verificationWarning`` to the response map).

CAMPUS-ISOLATION ENFORCEMENT (spec §9 + INTERVIEW_NOTES Module 2)
----------------------------------------------------------------
The Java controllers used a private ``resolveAdmin(auth)`` helper that:
  1. Loaded the authenticated user by email.
  2. Threw 400 if the admin had no campus assigned.
  3. Returned the admin.
Then each outlet-application review endpoint compared
``app.getCampus().getId()`` to ``admin.getCampus().getId()`` and threw 403 on
mismatch. Both checks are reproduced here verbatim — these are the campus-
isolation guards that prevent an ADMIN from Campus A touching Campus B's
applications.

TRANSACTION MODEL
-----------------
All mutating functions use ``db.flush()`` only — the router (FastAPI
dependency that owns the AsyncSession) commits on success and rolls back on
exception. This reproduces the Spring ``@Transactional`` boundary that lived
on each controller method.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.exceptions import ApiException
from app.models.admin_application import AdminApplication
from app.models.campus import Campus
from app.models.notification import Notification
from app.models.outlet import Outlet
from app.models.outlet_application import OutletApplication
from app.models.role import Role
from app.models.user import User
from app.security.password import hash_password
from app.services.document_verification_service import verify_application
from app.services.otp_service import generate_and_send_otp, is_email_verified, validate_otp

logger = logging.getLogger(__name__)

# Status constants (parity with AdminApplication.java / OutletApplication.java)
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"

# Anti-abuse cap shared by both application types — INTERVIEW_NOTES Module 2:
# "Both admin and manager applications are capped at 3 attempts if rejected —
# a simple anti-abuse measure, not because of any technical constraint."
MAX_ATTEMPTS = 3

# Notification type constants (parity with Notification.java)
TYPE_ADMIN_APP_APPROVED = "ADMIN_APP_APPROVED"
TYPE_OUTLET_APP_APPROVED = "OUTLET_APP_APPROVED"


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN APPLICATION — public submit + OTP sub-endpoints
# ══════════════════════════════════════════════════════════════════════════════


async def admin_send_otp(email: str | None, full_name: str | None, db: AsyncSession) -> dict[str, str]:
    """``POST /api/admin-applications/send-otp`` — email an OTP before applying.

    Direct port of ``AdminApplicationController.sendOtp``. The Java controller
    read ``body.getOrDefault("email", "")`` / ``body.getOrDefault("fullName",
    "Applicant")`` — we mirror the defaults (blank email → rejected by the
    contains-"@" check, missing name → "Applicant" fallback) and the same
    validation: ``email.isBlank() || !email.contains("@")`` → 400.
    """
    email = (email or "").lower().strip()
    full_name = (full_name or "").strip() or "Applicant"

    if email == "" or "@" not in email:
        raise ApiException("A valid email is required.", 400)

    # Reuses the registration OTP system (email_otp_tokens). Same fire-and-
    # forget send semantics as registration — see otp_service docstring.
    await generate_and_send_otp(email, full_name, db)
    return {"message": f"OTP sent to {email}. It expires in 10 minutes."}


async def admin_verify_otp(email: str | None, otp: str | None, db: AsyncSession) -> dict[str, str]:
    """``POST /api/admin-applications/verify-otp`` — validate the pre-apply OTP.

    Direct port of ``AdminApplicationController.verifyOtp``. Java's blank check
    on both fields is reproduced (``email.isBlank() || otp.isBlank()`` → 400);
    the actual validation delegates to ``validate_otp``.
    """
    email = (email or "").lower().strip()
    otp = (otp or "").strip()

    if email == "" or otp == "":
        raise ApiException("Email and OTP are both required.", 400)

    await validate_otp(email, otp, db)
    return {"message": "Email verified successfully.", "verified": "true"}


async def submit_admin_application(
    *,
    full_name: str,
    applicant_email: str,
    designation: str,
    id_card_photo_url: str,
    campus_name: str,
    campus_location: str,
    db: AsyncSession,
) -> AdminApplication:
    """``POST /api/admin-applications`` — submit a new admin application (public).

    Direct port of ``AdminApplicationController.submitApplication``. The order
    of checks is preserved exactly (later checks assume earlier ones passed —
    MIGRATION_RULES §2):

      1. Email must be OTP-verified (404/400 if not) — the application's whole
         premise is "the applicant owns this institutional email."
      2. Derived email domain must NOT already be a live campus (409).
      3. Derived email domain must NOT have an APPROVED application pending
         activation (409).
      4. Total attempts for this email must be < 3 (403 — the hard cap).
      5. No currently-PENDING application for this email (409 — one at a time).

    The ``campusEmailDomain`` is derived server-side from ``applicantEmail``
    (substring after '@') — never trusted from client input (matches Java).
    """
    email = applicant_email.lower().strip()

    # 1. Email must be OTP-verified via the /send-otp + /verify-otp sub-endpoints.
    if not await is_email_verified(email, db):
        raise ApiException(
            f"Please verify your email with the OTP sent to {email} "
            "before submitting your application.",
            400,
        )

    # Derive the campus email domain — this is the institutional identity proof.
    domain = email[email.index("@") + 1:]

    # 2. No existing live campus with this domain.
    existing_campus = (
        await db.execute(select(Campus).where(Campus.email_domain == domain))
    ).scalar_one_or_none()
    if existing_campus is not None:
        raise ApiException(
            "A campus with this email domain already exists on the platform.", 409
        )

    # 3. No existing APPROVED application for this domain (one waiting in the
    #    wings — don't allow a second).
    approved_for_domain = (
        await db.execute(
            select(AdminApplication).where(
                AdminApplication.campus_email_domain == domain,
                AdminApplication.status == STATUS_APPROVED,
            )
        )
    ).scalar_one_or_none()
    if approved_for_domain is not None:
        raise ApiException(
            "An approved application for this campus domain already exists.", 409
        )

    # 4. 3-attempt cap (counted across all statuses for this email).
    previous_attempts = await db.scalar(
        select(func.count()).select_from(AdminApplication).where(
            AdminApplication.applicant_email == email
        )
    )
    if previous_attempts is None:
        previous_attempts = 0
    if previous_attempts >= MAX_ATTEMPTS:
        raise ApiException(
            "You have reached the maximum number of applications (3) for this email.",
            403,
        )

    # 5. No currently-PENDING application for this email.
    pending_for_email = (
        await db.execute(
            select(AdminApplication).where(
                AdminApplication.applicant_email == email,
                AdminApplication.status == STATUS_PENDING,
            )
        )
    ).scalars().all()
    if pending_for_email:
        raise ApiException(
            "You already have a pending application. Please wait for a review.", 409
        )

    app = AdminApplication(
        full_name=full_name,
        applicant_email=email,
        designation=designation,
        # Base64 data-URI stored verbatim in TEXT (spec §4.5) — no truncation.
        id_card_photo_url=id_card_photo_url,
        campus_name=campus_name,
        campus_location=campus_location,
        campus_email_domain=domain,
        attempt_number=int(previous_attempts) + 1,
        status=STATUS_PENDING,
        created_at=datetime.now(),
    )
    db.add(app)
    await db.flush()  # populate app.id; caller commits
    return app


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN APPLICATION — SUPERADMIN review
# ══════════════════════════════════════════════════════════════════════════════


async def list_pending_admin_applications(db: AsyncSession) -> list[AdminApplication]:
    """``GET /api/admin-applications`` (SUPERADMIN) — list all PENDING apps."""
    result = await db.execute(
        select(AdminApplication)
        .where(AdminApplication.status == STATUS_PENDING)
        .order_by(AdminApplication.created_at.desc())
    )
    return list(result.scalars().all())


async def list_all_admin_applications(db: AsyncSession) -> list[AdminApplication]:
    """``GET /api/admin-applications/all`` (SUPERADMIN) — list all apps, any status."""
    result = await db.execute(select(AdminApplication))
    return list(result.scalars().all())


async def approve_admin_application(
    app_id: int, message: str | None, temporary_password: str | None, db: AsyncSession
) -> dict[str, Any]:
    """``PATCH /api/admin-applications/{id}/approve`` (SUPERADMIN).

    Direct port of ``AdminApplicationController.approveApplication``. Order of
    operations is preserved exactly (MIGRATION_RULES §2):

      1. Load app, 404 if missing.
      2. Must be PENDING (400 otherwise).
      3. temporaryPassword required (400 if blank).
      4. Create Campus (ACTIVE).
      5. Look up ADMIN role (500 if missing — DataInitializer didn't run).
      6. Create the ADMIN User (BCrypt-hashed temp password), linked to campus.
      7. Mark app APPROVED + link created campus + reviewed_at.
      8. Insert Notification row for the new admin (welcome message, default
         if no custom message provided).
      9. Return {message, campusId, adminUserId}.

    Returns a dict (not the entity) because the Java controller returned a
    ``Map<String, Object>`` — ids are JSON numbers here.
    """
    app = await _load_admin_app_or_404(app_id, db)

    if app.status != STATUS_PENDING:
        raise ApiException("Application is not in PENDING state", 400)
    if temporary_password is None or temporary_password.strip() == "":
        raise ApiException("temporaryPassword is required when approving", 400)

    # 4. Create Campus (ACTIVE) — this is the moment a new tenant appears.
    campus = Campus(
        name=app.campus_name,
        location=app.campus_location,
        email_domain=app.campus_email_domain,
        status="ACTIVE",
        created_at=datetime.now(),
    )
    db.add(campus)

    # 5. Look up ADMIN role.
    admin_role = (
        await db.execute(select(Role).where(Role.name == "ADMIN"))
    ).scalar_one_or_none()
    if admin_role is None:
        raise ApiException("ADMIN role not seeded — run DataInitializer", 500)

    # 6. Create ADMIN user. Default user-shape values mirror Java's User
    #    constructor (is_active=true, no_show_count=0, penalty=0, ACTIVE).
    admin_user = User(
        full_name=app.full_name,
        email=app.applicant_email,
        password_hash=hash_password(temporary_password),
        role=admin_role,
        campus=campus,
        is_active=True,
        no_show_count=0,
        pending_penalty_amount=0.0,
        account_status="ACTIVE",
        created_at=datetime.now(),
    )
    db.add(admin_user)

    # 7. Mark the application APPROVED + link the created campus.
    app.status = STATUS_APPROVED
    app.created_campus = campus
    app.reviewed_at = datetime.now()

    # 8. Welcome notification. Default message mirrors the Java fallback.
    welcome_msg = (
        message
        if message is not None and message.strip() != ""
        else (
            f'Congratulations! Your application to manage campus "{campus.name}" '
            "has been approved. Please log in with the credentials shared with you "
            "via email."
        )
    )
    db.add(
        Notification(
            user=admin_user,
            title="Admin Application Approved",
            message=welcome_msg,
            type=TYPE_ADMIN_APP_APPROVED,
            is_read=False,
            created_at=datetime.now(),
        )
    )

    await db.flush()  # populate campus.id + admin_user.id before returning them
    return {
        "message": "Application approved. Campus and admin account created.",
        "campus_id": campus.id,
        "admin_user_id": admin_user.id,
    }


async def reject_admin_application(
    app_id: int, message: str | None, db: AsyncSession
) -> dict[str, str]:
    """``PATCH /api/admin-applications/{id}/reject`` (SUPERADMIN).

    Direct port of ``AdminApplicationController.rejectApplication``. Order:
      1. Load app, 404 if missing.
      2. Must be PENDING (400 otherwise).
      3. Default reason if no message provided.
      4. Mark REJECTED + record reason + reviewed_at.
      5. Compute remainingAttempts = MAX_ATTEMPTS - countByEmail; clamp >= 0.
      6. Return {message, reason, remainingAttempts} (all stringified).
    """
    app = await _load_admin_app_or_404(app_id, db)

    if app.status != STATUS_PENDING:
        raise ApiException("Application is not in PENDING state", 400)

    reason = (
        message
        if message is not None and message.strip() != ""
        else "Your application did not meet the requirements at this time."
    )

    app.status = STATUS_REJECTED
    app.rejection_reason = reason
    app.reviewed_at = datetime.now()

    total_attempts = await db.scalar(
        select(func.count()).select_from(AdminApplication).where(
            AdminApplication.applicant_email == app.applicant_email
        )
    )
    if total_attempts is None:
        total_attempts = 0
    remaining = max(0, MAX_ATTEMPTS - int(total_attempts))

    return {
        "message": "Application rejected.",
        "reason": reason,
        # Java stringified remainingAttempts via String.valueOf — parity.
        "remaining_attempts": str(remaining),
    }


async def _load_admin_app_or_404(app_id: int, db: AsyncSession) -> AdminApplication:
    """Load an admin application by id or raise 404. Eager-loads created_campus."""
    app = (
        await db.execute(
            select(AdminApplication)
            .options(joinedload(AdminApplication.created_campus))
            .where(AdminApplication.id == app_id)
        )
    ).scalar_one_or_none()
    if app is None:
        raise ApiException("Application not found", 404)
    return app


# ══════════════════════════════════════════════════════════════════════════════
# OUTLET APPLICATION — public submit
# ══════════════════════════════════════════════════════════════════════════════


async def submit_outlet_application(
    *,
    manager_name: str,
    manager_email: str,
    outlet_name: str,
    outlet_description: str | None,
    campus_id: int,
    avg_prep_time: int,
    license_doc_url: str,
    outlet_photo_url: str | None,
    fssai_license_number: str | None,
    gstin: str | None,
    pan_number: str | None,
    bank_account_number: str | None,
    bank_ifsc_code: str | None,
    db: AsyncSession,
) -> tuple[OutletApplication, None]:
    """``POST /api/outlet-applications`` — submit a new outlet application (public).

    Direct port of ``OutletApplicationController.submitApplication``. Order of
    checks preserved exactly (MIGRATION_RULES §2):

      1. Campus must exist (404 otherwise).
      2. 3-attempt cap (counted across all statuses for this manager email).
      3. No currently-PENDING application for this email.
      4. Build + save the application. Document fields are trimmed/upper-cased
         exactly as the Java constructor did (gstin/pan/ifsc upper-cased).
      5. Run document verification (Layer 1 only — see document_verification_service).

    NOTE: Outlet managers are NOT required to use the campus email domain —
    outlet staff commonly use personal email (Gmail etc.). This matches Java.

    Returns a tuple ``(app, None)`` for forward-compat — Java's @Async returned
    void; the verification result is reachable via app.verification_report.
    """
    # 1. Campus lookup.
    campus = (
        await db.execute(select(Campus).where(Campus.id == campus_id))
    ).scalar_one_or_none()
    if campus is None:
        raise ApiException("Campus not found", 404)

    manager_email = manager_email.lower().strip()

    # 2. 3-attempt cap.
    previous_attempts = await db.scalar(
        select(func.count()).select_from(OutletApplication).where(
            OutletApplication.manager_email == manager_email
        )
    )
    if previous_attempts is None:
        previous_attempts = 0
    if previous_attempts >= MAX_ATTEMPTS:
        raise ApiException(
            "You have reached the maximum number of applications (3) for this email.",
            403,
        )

    # 3. No currently-PENDING application for this email.
    pending_for_email = (
        await db.execute(
            select(OutletApplication).where(
                OutletApplication.manager_email == manager_email,
                OutletApplication.status == STATUS_PENDING,
            )
        )
    ).scalars().all()
    if pending_for_email:
        raise ApiException(
            "You already have a pending application. Please wait for a review.", 409
        )

    # 4. Build the application. Document fields trimmed/upper-cased to match
    #    the Java full-constructor's normalization (gstin/pan/ifsc .toUpperCase()).
    app = OutletApplication(
        manager_name=manager_name,
        manager_email=manager_email,
        outlet_name=outlet_name,
        outlet_description=outlet_description,
        avg_prep_time=avg_prep_time,
        # Base64 license document — TEXT column, stored verbatim (spec §4.5).
        license_doc_url=license_doc_url,
        # Base64 outlet photo — TEXT column, optional (spec §4.5).
        outlet_photo_url=outlet_photo_url,
        campus=campus,
        attempt_number=int(previous_attempts) + 1,
        status=STATUS_PENDING,
        created_at=datetime.now(),
        fssai_license_number=(
            fssai_license_number.strip() if fssai_license_number else None
        ),
        gstin=(gstin.strip().upper() if gstin else None),
        pan_number=(pan_number.strip().upper() if pan_number else None),
        bank_account_number=(
            bank_account_number.strip() if bank_account_number else None
        ),
        bank_ifsc_code=(
            bank_ifsc_code.strip().upper() if bank_ifsc_code else None
        ),
    )
    db.add(app)
    await db.flush()  # populate app.id before verification references it

    # 5. Document verification (Layer 1 only — synchronous in this port; see
    #    document_verification_service docstring for the async/sync divergence).
    await verify_application(app, db)

    return app, None


# ══════════════════════════════════════════════════════════════════════════════
# OUTLET APPLICATION — ADMIN review (campus-scoped)
# ══════════════════════════════════════════════════════════════════════════════


async def list_pending_outlet_applications_for_admin(
    admin: User, db: AsyncSession
) -> list[OutletApplication]:
    """``GET /api/outlet-applications/pending`` (ADMIN) — pending for admin's campus."""
    admin = _require_admin_with_campus(admin)
    result = await db.execute(
        select(OutletApplication)
        .where(
            OutletApplication.campus_id == admin.campus_id,
            OutletApplication.status == STATUS_PENDING,
        )
        .order_by(OutletApplication.created_at.desc())
    )
    return list(result.scalars().all())


async def list_all_outlet_applications_for_admin(
    admin: User, db: AsyncSession
) -> list[OutletApplication]:
    """``GET /api/outlet-applications/all`` (ADMIN) — all (any status) for admin's campus."""
    admin = _require_admin_with_campus(admin)
    result = await db.execute(
        select(OutletApplication)
        .where(OutletApplication.campus_id == admin.campus_id)
        .order_by(OutletApplication.created_at.desc())
    )
    return list(result.scalars().all())


async def list_pending_outlet_applications_platform_wide(
    db: AsyncSession,
) -> list[OutletApplication]:
    """``GET /api/outlet-applications/platform-pending`` (SUPERADMIN) — all pending."""
    result = await db.execute(
        select(OutletApplication)
        .where(OutletApplication.status == STATUS_PENDING)
        .order_by(OutletApplication.created_at.desc())
    )
    return list(result.scalars().all())


async def get_outlet_application_verification_report(
    app_id: int, admin: User, db: AsyncSession
) -> Any:
    """``GET /api/outlet-applications/{id}/verification-report`` (ADMIN).

    Direct port of ``OutletApplicationController.getVerificationReport``:
      1. Resolve admin (must have a campus, else 400).
      2. Load application, 404 if missing.
      3. Application's campus must match admin's campus (403 otherwise) —
         this is the campus-isolation guard.
      4. Load the linked VerificationReport, 404 if not yet available.

    Returns the ``VerificationReport`` row (router serializes it).
    """
    from app.models.verification_report import VerificationReport  # local import — avoid cycle at module load

    admin = _require_admin_with_campus(admin)
    app = await _load_outlet_app_or_404(app_id, db)

    if app.campus_id != admin.campus_id:
        raise ApiException("You can only view reports for your own campus.", 403)

    report = (
        await db.execute(
            select(VerificationReport).where(
                VerificationReport.outlet_application_id == app_id
            )
        )
    ).scalar_one_or_none()
    if report is None:
        raise ApiException(
            "Verification report not yet available — please retry in a few seconds.",
            404,
        )
    return report


async def approve_outlet_application(
    app_id: int,
    message: str | None,
    temporary_password: str | None,
    admin: User,
    db: AsyncSession,
) -> dict[str, Any]:
    """``PATCH /api/outlet-applications/{id}/approve`` (ADMIN, campus-scoped).

    Direct port of ``OutletApplicationController.approveApplication``. Order of
    operations preserved exactly (MIGRATION_RULES §2):

      1. Resolve admin (400 if no campus).
      2. Load application, 404 if missing.
      3. Application's campus must match admin's campus (403 — campus isolation).
      4. Application must be PENDING (400 otherwise).
      5. temporaryPassword required (400 if blank).
      6. Pre-compute verificationFailed flag from the linked report (does NOT
         block approval — Java only added a warning to the response).
      7. Look up MANAGER role (500 if missing).
      8. Create MANAGER user (BCrypt-hashed temp password), linked to app's campus.
      9. Create Outlet (PENDING_LAUNCH) with bank details pre-filled from app.
     10. Mark application APPROVED + link created outlet + reviewed_at.
     11. Insert Notification row for the new manager.
     12. Return {message, outletId, managerUserId, outletStatus, [verificationWarning]}.
    """
    admin = _require_admin_with_campus(admin)
    app = await _load_outlet_app_or_404(app_id, db)

    if app.campus_id != admin.campus_id:
        raise ApiException("You can only review applications for your own campus.", 403)
    if app.status != STATUS_PENDING:
        raise ApiException("Application is not in PENDING state", 400)
    if temporary_password is None or temporary_password.strip() == "":
        raise ApiException("temporaryPassword is required when approving", 400)

    # 6. Verification-failed flag — does NOT block approval. The Java code
    #    looked up the report, mapped to STATUS_FAILED, and orElse(false).
    verification_failed = False
    if app.verification_report is not None:
        verification_failed = app.verification_report.overall_status == "FAILED"

    # 7. MANAGER role lookup.
    manager_role = (
        await db.execute(select(Role).where(Role.name == "MANAGER"))
    ).scalar_one_or_none()
    if manager_role is None:
        raise ApiException("MANAGER role not seeded — run DataInitializer", 500)

    # 8. Create MANAGER user.
    manager = User(
        full_name=app.manager_name,
        email=app.manager_email,
        password_hash=hash_password(temporary_password),
        role=manager_role,
        campus=app.campus,
        is_active=True,
        no_show_count=0,
        pending_penalty_amount=0.0,
        account_status="ACTIVE",
        created_at=datetime.now(),
    )
    db.add(manager)

    # 9. Create Outlet in PENDING_LAUNCH — the manager must add menu + launch
    #    before students can see it (handled later in OutletController).
    #    Outlet.java defines the status string constants; the SQLAlchemy model
    #    keeps them as plain String columns (spec §10) so we use the literal
    #    here, matching what Java's ``new Outlet(..., Outlet.STATUS_PENDING_LAUNCH, ...)``
    #    wrote to the DB.
    outlet = Outlet(
        name=app.outlet_name,
        campus=app.campus,
        manager=manager,
        status="PENDING_LAUNCH",
        avg_prep_time=app.avg_prep_time,
        photo_url=app.outlet_photo_url,
        created_at=datetime.now(),
    )
    # Pre-fill bank details from the application if provided — Java did this
    # via three independent ``if (app.getX() != null) outlet.setX(...)`` calls.
    if app.bank_account_number is not None:
        outlet.bank_account_number = app.bank_account_number
    if app.bank_ifsc_code is not None:
        outlet.bank_ifsc_code = app.bank_ifsc_code
    if app.manager_name is not None:
        outlet.bank_account_holder_name = app.manager_name
    db.add(outlet)

    # 10. Mark the application APPROVED + link the created outlet.
    app.status = STATUS_APPROVED
    app.created_outlet = outlet
    app.reviewed_at = datetime.now()

    # 11. Notification to the new manager.
    msg = (
        message
        if message is not None and message.strip() != ""
        else (
            f'Your outlet "{outlet.name}" has been approved! '
            "Log in with the credentials shared with you, add your menu items, "
            "and click 'Launch Outlet' to go live."
        )
    )
    db.add(
        Notification(
            user=manager,
            title="Outlet Application Approved",
            message=msg,
            type=TYPE_OUTLET_APP_APPROVED,
            is_read=False,
            created_at=datetime.now(),
        )
    )

    await db.flush()  # populate outlet.id + manager.id

    response: dict[str, Any] = {
        "message": "Application approved. Outlet and manager account created.",
        "outlet_id": outlet.id,
        "manager_user_id": manager.id,
        "outlet_status": outlet.status,
    }
    if verification_failed:
        response["verification_warning"] = (
            "⚠️ This application had a FAILED verification score. "
            "You have approved it manually."
        )
    return response


async def reject_outlet_application(
    app_id: int, message: str | None, admin: User, db: AsyncSession
) -> dict[str, str]:
    """``PATCH /api/outlet-applications/{id}/reject`` (ADMIN, campus-scoped).

    Direct port of ``OutletApplicationController.rejectApplication``. Same
    campus-isolation + PENDING-state checks as approve, then default reason +
    mark REJECTED + remainingAttempts computation.
    """
    admin = _require_admin_with_campus(admin)
    app = await _load_outlet_app_or_404(app_id, db)

    if app.campus_id != admin.campus_id:
        raise ApiException("You can only review applications for your own campus.", 403)
    if app.status != STATUS_PENDING:
        raise ApiException("Application is not in PENDING state", 400)

    reason = (
        message
        if message is not None and message.strip() != ""
        else "Your application did not meet the requirements at this time."
    )

    app.status = STATUS_REJECTED
    app.rejection_reason = reason
    app.reviewed_at = datetime.now()

    total_attempts = await db.scalar(
        select(func.count()).select_from(OutletApplication).where(
            OutletApplication.manager_email == app.manager_email
        )
    )
    if total_attempts is None:
        total_attempts = 0
    remaining = max(0, MAX_ATTEMPTS - int(total_attempts))

    return {
        "message": "Application rejected.",
        "reason": reason,
        "remaining_attempts": str(remaining),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _require_admin_with_campus(admin: User) -> User:
    """Equivalent of Java's ``resolveAdmin``.

    Throws 400 if the authenticated admin has no campus assigned (e.g. a
    SuperAdmin calling an ADMIN-only outlet-app endpoint — they don't have a
    campus to scope by, so the request makes no sense). The campus comparison
    itself happens per-endpoint against each application's campus_id.

    Note: ``admin.campus_id`` is read directly (not via the relationship) so
    this helper doesn't trigger a lazy-load in async SQLAlchemy. The auth dep
    already loaded the user with role joined; campus_id is a scalar FK column.
    """
    if admin.campus_id is None:
        raise ApiException("Admin is not assigned to any campus", 400)
    return admin


async def _load_outlet_app_or_404(
    app_id: int, db: AsyncSession
) -> OutletApplication:
    """Load an outlet application by id or raise 404.

    Eager-loads ``campus``, ``created_outlet``, and ``verification_report``
    because the response serialization touches all three, and async SQLAlchemy
    cannot lazy-load on attribute access.
    """
    app = (
        await db.execute(
            select(OutletApplication)
            .options(
                joinedload(OutletApplication.campus),
                joinedload(OutletApplication.created_outlet),
                joinedload(OutletApplication.verification_report),
            )
            .where(OutletApplication.id == app_id)
        )
    ).scalar_one_or_none()
    if app is None:
        raise ApiException("Application not found", 404)
    return app


async def reload_outlet_application_for_response(
    app_id: int, db: AsyncSession
) -> OutletApplication:
    """Public wrapper around the eager-loading loader.

    Routers call this after ``db.commit()`` on submit/approve to re-fetch the
    application with all response-touched relationships populated (campus,
    created_outlet, verification_report). Without this, async SQLAlchemy would
    raise MissingGreenlet on the response serializer touching a lazy relationship
    that was never loaded in this session.
    """
    return await _load_outlet_app_or_404(app_id, db)
