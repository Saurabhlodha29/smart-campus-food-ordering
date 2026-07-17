"""Admin-application router — ``/api/admin-applications/*`` endpoints.

Source of truth: ``AdminApplicationController.java`` (Spring Boot
``@RestController @RequestMapping("/api/admin-applications")``).

Authorization (spec §9 — reproduced exactly):
  - PUBLIC (no JWT): POST /api/admin-applications
                     POST /api/admin-applications/send-otp
                     POST /api/admin-applications/verify-otp
  - SUPERADMIN only: GET  /api/admin-applications
                     GET  /api/admin-applications/all
                     PATCH /api/admin-applications/{id}/approve
                     PATCH /api/admin-applications/{id}/reject

The router is thin (parse → delegate to service → wrap in response model); no
business logic lives here (MIGRATION_RULES §6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.admin_application import AdminApplication
from app.schemas.admin_application import (
    AdminApplicationRequest,
    AdminApplicationResponse,
    AdminApplicationReviewRequest,
    AdminApproveResponse,
    AdminOtpMessageResponse,
    AdminRejectResponse,
    AdminSendOtpRequest,
    AdminVerifyOtpRequest,
)
from app.security.deps import require_role
from app.services import application_service

router = APIRouter(prefix="/api/admin-applications", tags=["admin-applications"])


# ── PUBLIC — Email OTP verification (must happen before submitting) ───────────


@router.post("/send-otp", response_model=AdminOtpMessageResponse)
async def send_otp(
    body: AdminSendOtpRequest, db: AsyncSession = Depends(get_db)
) -> AdminOtpMessageResponse:
    """Email an OTP before the applicant submits. Mirrors AdminApplicationController.sendOtp."""
    result = await application_service.admin_send_otp(body.email, body.full_name, db)
    await db.commit()
    return AdminOtpMessageResponse(**result)


@router.post("/verify-otp", response_model=AdminOtpMessageResponse)
async def verify_otp(
    body: AdminVerifyOtpRequest, db: AsyncSession = Depends(get_db)
) -> AdminOtpMessageResponse:
    """Validate the pre-apply OTP. Mirrors AdminApplicationController.verifyOtp."""
    result = await application_service.admin_verify_otp(body.email, body.otp, db)
    await db.commit()
    return AdminOtpMessageResponse(**result)


# ── PUBLIC — Submit a new admin application ───────────────────────────────────


@router.post(
    "",
    response_model=AdminApplicationResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def submit_application(
    body: AdminApplicationRequest, db: AsyncSession = Depends(get_db)
) -> AdminApplicationResponse:
    """Submit a new admin application (public — pre-account).

    Mirrors AdminApplicationController.submitApplication (@ResponseStatus CREATED).
    Returns 201 with the saved application (raw entity serialization shape).
    """
    app: AdminApplication = await application_service.submit_admin_application(
        full_name=body.full_name,
        applicant_email=str(body.applicant_email),
        designation=body.designation,
        id_card_photo_url=body.id_card_photo_url,
        campus_name=body.campus_name,
        campus_location=body.campus_location,
        db=db,
    )
    await db.commit()
    # Refresh to load the (nullable) created_campus relationship for response
    # serialization — submit never sets it, but exclude_none drops it anyway.
    await db.refresh(app)
    return AdminApplicationResponse.model_validate(app, from_attributes=True)


# ── SUPERADMIN — Dashboard ────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[AdminApplicationResponse],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("SUPERADMIN"))],
)
async def get_pending_applications(
    db: AsyncSession = Depends(get_db),
) -> list[AdminApplicationResponse]:
    """List all PENDING admin applications. SUPERADMIN only."""
    apps = await application_service.list_pending_admin_applications(db)
    return [
        AdminApplicationResponse.model_validate(a, from_attributes=True) for a in apps
    ]


@router.get(
    "/all",
    response_model=list[AdminApplicationResponse],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("SUPERADMIN"))],
)
async def get_all_applications(
    db: AsyncSession = Depends(get_db),
) -> list[AdminApplicationResponse]:
    """List ALL admin applications (any status). SUPERADMIN only."""
    apps = await application_service.list_all_admin_applications(db)
    return [
        AdminApplicationResponse.model_validate(a, from_attributes=True) for a in apps
    ]


# ── SUPERADMIN — Approve ──────────────────────────────────────────────────────


@router.patch(
    "/{app_id}/approve",
    response_model=AdminApproveResponse,
    dependencies=[Depends(require_role("SUPERADMIN"))],
)
async def approve_application(
    app_id: int,
    body: AdminApplicationReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminApproveResponse:
    """Approve a pending admin application — creates Campus + ADMIN user.

    SUPERADMIN only. Mirrors AdminApplicationController.approveApplication.
    """
    result = await application_service.approve_admin_application(
        app_id, body.message, body.temporary_password, db
    )
    await db.commit()
    return AdminApproveResponse(**result)


# ── SUPERADMIN — Reject ───────────────────────────────────────────────────────


@router.patch(
    "/{app_id}/reject",
    response_model=AdminRejectResponse,
    dependencies=[Depends(require_role("SUPERADMIN"))],
)
async def reject_application(
    app_id: int,
    body: AdminApplicationReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminRejectResponse:
    """Reject a pending admin application. SUPERADMIN only.

    Note: Java accepted this body as a bare ``@RequestBody`` (no @Valid), so a
    missing body would have deserialized to null. The Pydantic schema here
    makes both fields optional to preserve that permissiveness; the service
    applies the default reason if ``message`` is absent or blank.
    """
    result = await application_service.reject_admin_application(
        app_id, body.message, db
    )
    await db.commit()
    return AdminRejectResponse(**result)
