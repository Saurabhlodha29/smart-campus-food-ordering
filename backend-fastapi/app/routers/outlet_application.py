"""Outlet-application router — ``/api/outlet-applications/*`` endpoints.

Source of truth: ``OutletApplicationController.java`` (Spring Boot
``@RestController @RequestMapping("/api/outlet-applications")``).

Authorization (spec §9 — reproduced exactly):
  - PUBLIC (no JWT): POST /api/outlet-applications
  - ADMIN only:      GET   /api/outlet-applications/pending
                     GET   /api/outlet-applications/all
                     GET   /api/outlet-applications/{id}/verification-report
                     PATCH /api/outlet-applications/{id}/approve
                     PATCH /api/outlet-applications/{id}/reject
  - SUPERADMIN only: GET   /api/outlet-applications/platform-pending

The router is thin (parse → delegate to service → wrap in response model); no
business logic lives here (MIGRATION_RULES §6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.models.verification_report import VerificationReport
from app.schemas.outlet_application import (
    OutletApplicationResponse,
    OutletApplicationRequest,
    OutletApplicationReviewRequest,
    OutletApproveResponse,
    OutletRejectResponse,
    VerificationReportResponse,
)
from app.security.deps import require_role
from app.services import application_service

router = APIRouter(prefix="/api/outlet-applications", tags=["outlet-applications"])


# ── PUBLIC — Submit ───────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=OutletApplicationResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def submit_application(
    body: OutletApplicationRequest, db: AsyncSession = Depends(get_db)
) -> OutletApplicationResponse:
    """Submit a new outlet application (public — manager has no account yet).

    Mirrors OutletApplicationController.submitApplication (@ResponseStatus CREATED).
    Triggers Layer-1 document verification synchronously after the save.
    """
    app, _ = await application_service.submit_outlet_application(
        manager_name=body.manager_name,
        manager_email=str(body.manager_email),
        outlet_name=body.outlet_name,
        outlet_description=body.outlet_description,
        campus_id=body.campus_id,
        avg_prep_time=body.avg_prep_time,
        license_doc_url=body.license_doc_url,
        outlet_photo_url=body.outlet_photo_url,
        fssai_license_number=body.fssai_license_number,
        gstin=body.gstin,
        pan_number=body.pan_number,
        bank_account_number=body.bank_account_number,
        bank_ifsc_code=body.bank_ifsc_code,
        db=db,
    )
    await db.commit()
    # Reload with the now-populated verification_report + created_outlet +
    # campus so the response serializer has every nested field available.
    refreshed = await application_service.reload_outlet_application_for_response(
        app.id, db
    )
    return OutletApplicationResponse.model_validate(refreshed, from_attributes=True)


# ── ADMIN — pending/all for their own campus ──────────────────────────────────


@router.get(
    "/pending",
    response_model=list[OutletApplicationResponse],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def get_pending_for_my_campus(
    admin: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> list[OutletApplicationResponse]:
    """List PENDING outlet applications for the admin's campus. ADMIN only."""
    apps = await application_service.list_pending_outlet_applications_for_admin(admin, db)
    return [
        OutletApplicationResponse.model_validate(a, from_attributes=True) for a in apps
    ]


@router.get(
    "/all",
    response_model=list[OutletApplicationResponse],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def get_all_for_my_campus(
    admin: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> list[OutletApplicationResponse]:
    """List ALL outlet applications (any status) for the admin's campus. ADMIN only."""
    apps = await application_service.list_all_outlet_applications_for_admin(admin, db)
    return [
        OutletApplicationResponse.model_validate(a, from_attributes=True) for a in apps
    ]


# ── ADMIN — verification report ───────────────────────────────────────────────


@router.get(
    "/{app_id}/verification-report",
    response_model=VerificationReportResponse,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def get_verification_report(
    app_id: int,
    admin: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> VerificationReportResponse:
    """View the verification report for one outlet application. ADMIN only.

    Campus-isolated: the admin can only fetch reports for their own campus
    (enforced in the service via ``app.campus_id != admin.campus_id`` → 403).
    """
    report: VerificationReport = (
        await application_service.get_outlet_application_verification_report(
            app_id, admin, db
        )
    )
    return VerificationReportResponse.model_validate(report, from_attributes=True)


# ── SUPERADMIN — platform-wide pending ────────────────────────────────────────


@router.get(
    "/platform-pending",
    response_model=list[OutletApplicationResponse],
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("SUPERADMIN"))],
)
async def get_all_pending_platform_wide(
    db: AsyncSession = Depends(get_db),
) -> list[OutletApplicationResponse]:
    """List ALL PENDING outlet applications platform-wide. SUPERADMIN only."""
    apps = await application_service.list_pending_outlet_applications_platform_wide(db)
    return [
        OutletApplicationResponse.model_validate(a, from_attributes=True) for a in apps
    ]


# ── ADMIN — Approve ───────────────────────────────────────────────────────────


@router.patch(
    "/{app_id}/approve",
    response_model=OutletApproveResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def approve_application(
    app_id: int,
    body: OutletApplicationReviewRequest,
    admin: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> OutletApproveResponse:
    """Approve a pending outlet application — creates Manager user + Outlet.

    ADMIN only, scoped to the admin's own campus.
    """
    result = await application_service.approve_outlet_application(
        app_id, body.message, body.temporary_password, admin, db
    )
    await db.commit()
    return OutletApproveResponse(**result)


# ── ADMIN — Reject ────────────────────────────────────────────────────────────


@router.patch(
    "/{app_id}/reject",
    response_model=OutletRejectResponse,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def reject_application(
    app_id: int,
    body: OutletApplicationReviewRequest,
    admin: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> OutletRejectResponse:
    """Reject a pending outlet application. ADMIN only, scoped to own campus."""
    result = await application_service.reject_outlet_application(
        app_id, body.message, admin, db
    )
    await db.commit()
    return OutletRejectResponse(**result)
