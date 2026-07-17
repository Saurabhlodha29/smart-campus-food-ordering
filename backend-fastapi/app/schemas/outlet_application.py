"""Pydantic request/response schemas for the outlet-application endpoints.

Mirrors the Java DTOs and raw ``OutletApplication`` entity serialization
produced by Spring Boot's ``OutletApplicationController`` so the frontend
contract (camelCase JSON) stays identical after the FastAPI migration.

Mirrored Java classes:
    - OutletApplicationRequest                 -> OutletApplicationRequest
    - OutletApplicationReviewRequest           -> OutletApplicationReviewRequest
    - OutletApplication (raw entity response)  -> OutletApplicationResponse
    - VerificationReport (raw entity response) -> VerificationReportResponse
    - (no DTO — Map<String, Object>)           -> OutletApproveResponse
    - (no DTO — Map<String, String>)           -> OutletRejectResponse
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

# Same @Size(max = 4_000_000) cap as Java for base64 image payload fields.
_MAX_PHOTO_CHARS = 4_000_000


class OutletApplicationRequest(BaseModel):
    """Body for ``POST /api/outlet-applications`` (public — no account yet).

    Mirrors Java ``OutletApplicationRequest``:
        - managerName:         @NotBlank, max 120
        - managerEmail:        @Email, max 150
        - outletName:          @NotBlank, max 150
        - outletDescription:   optional (TEXT)
        - campusId:            @NotNull Long
        - avgPrepTime:         @Min(1) int
        - licenseDocUrl:       @NotBlank, @Size(max = 4_000_000)  ← base64, TEXT
        - outletPhotoUrl:      optional, @Size(max = 4_000_000)   ← base64, TEXT
        - fssaiLicenseNumber:  optional, max 20
        - gstin:               optional, max 20
        - panNumber:           optional, max 15
        - bankAccountNumber:   optional, max 25
        - bankIfscCode:        optional, max 15
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    manager_name: str = Field(..., alias="managerName", min_length=1, max_length=120)
    manager_email: EmailStr = Field(..., alias="managerEmail", max_length=150)
    outlet_name: str = Field(..., alias="outletName", min_length=1, max_length=150)
    outlet_description: Optional[str] = Field(default=None, alias="outletDescription")
    campus_id: int = Field(..., alias="campusId")
    avg_prep_time: int = Field(..., alias="avgPrepTime", ge=1)
    # Base64 license document image — TEXT column (spec §4.5)
    license_doc_url: str = Field(
        ..., alias="licenseDocUrl", min_length=1, max_length=_MAX_PHOTO_CHARS
    )
    # Optional base64 outlet photo — TEXT column (spec §4.5)
    outlet_photo_url: Optional[str] = Field(
        default=None, alias="outletPhotoUrl", max_length=_MAX_PHOTO_CHARS
    )

    # Document verification fields (Layer-1 format-only validation in service)
    fssai_license_number: Optional[str] = Field(
        default=None, alias="fssaiLicenseNumber", max_length=20
    )
    gstin: Optional[str] = Field(default=None, alias="gstin", max_length=20)
    pan_number: Optional[str] = Field(default=None, alias="panNumber", max_length=15)
    bank_account_number: Optional[str] = Field(
        default=None, alias="bankAccountNumber", max_length=25
    )
    bank_ifsc_code: Optional[str] = Field(
        default=None, alias="bankIfscCode", max_length=15
    )


class OutletApplicationReviewRequest(BaseModel):
    """Body for ``PATCH /api/outlet-applications/{id}/approve`` and ``/reject``.

    Mirrors Java ``OutletApplicationReviewRequest``:
        - message:           optional reason/note shown to the manager
        - temporaryPassword: required on approve, ignored on reject
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    message: Optional[str] = None
    temporary_password: Optional[str] = Field(default=None, alias="temporaryPassword")


# ── Response models ────────────────────────────────────────────────────────────


class _CampusRef(BaseModel):
    """Nested campus reference as serialized inside an outlet application.

    Mirrors the JPA ``@ManyToOne campus`` serialization shape — scalar fields
    only, no recursion into users/outlets.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    name: str
    location: str
    email_domain: str = Field(..., alias="emailDomain")
    status: str


class _CreatedOutletRef(BaseModel):
    """Nested outlet reference set on APPROVED applications.

    JPA serializes the ``createdOutlet`` @ManyToOne when non-null. To avoid
    recursing into Outlet.manager (a User) → User.managed_outlets (Outlets) →
    …, we emit only the scalar outlet fields plus the manager id, matching what
    the frontend actually consumes on the review screen.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    name: str
    campus_id: int
    manager_id: int
    status: str
    avg_prep_time: int
    photo_url: Optional[str] = None
    launched_at: Optional[datetime] = None
    created_at: datetime


class VerificationReportResponse(BaseModel):
    """Raw ``VerificationReport`` entity serialization.

    Reproduces the camelCase field names the frontend deserializes on the
    review screen. ``fssai_name_match_score`` is a float (Java Double, nullable)
    and ``overall_score`` is an int.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    outlet_application_id: int
    fssai_verified: Optional[bool] = None
    fssai_registered_name: Optional[str] = None
    fssai_expiry_date: Optional[str] = None
    fssai_name_match_score: Optional[float] = None
    fssai_name_mismatch: bool
    fssai_note: Optional[str] = None
    gst_verified: Optional[bool] = None
    gst_business_name: Optional[str] = None
    gst_name_mismatch: bool
    gst_note: Optional[str] = None
    pan_format_valid: bool
    pan_note: Optional[str] = None
    bank_ifsc_valid: Optional[bool] = None
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_note: Optional[str] = None
    overall_score: int
    overall_status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class OutletApplicationResponse(BaseModel):
    """Raw ``OutletApplication`` entity serialization.

    Reproduces camelCase field names. The nested ``campus`` is always present
    (it's a non-null FK). The nested ``created_outlet`` and
    ``verification_report`` are only present when set; we use route-level
    ``response_model_exclude_none`` to drop them when null.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    manager_name: str
    manager_email: str
    outlet_name: str
    outlet_description: Optional[str] = None
    avg_prep_time: int
    license_doc_url: str
    outlet_photo_url: Optional[str] = None
    fssai_license_number: Optional[str] = None
    gstin: Optional[str] = None
    pan_number: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    campus_id: int
    status: str
    rejection_reason: Optional[str] = None
    attempt_number: int
    reviewed_at: Optional[datetime] = None
    created_outlet_id: Optional[int] = None
    created_at: datetime
    campus: _CampusRef
    created_outlet: Optional[_CreatedOutletRef] = None
    verification_report: Optional[VerificationReportResponse] = None


class OutletApproveResponse(BaseModel):
    """``Map<String, Object>`` returned by PATCH /{id}/approve.

    Java returned ``{message, outletId, managerUserId, outletStatus}`` and
    conditionally ``verificationWarning``. The first three ids are boxed Long
    (serialized as JSON numbers); ``outletStatus`` is a String.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str
    outlet_id: int
    manager_user_id: int
    outlet_status: str
    verification_warning: Optional[str] = None


class OutletRejectResponse(BaseModel):
    """``Map<String, String>`` returned by PATCH /{id}/reject.

    Java stringified every value (including remainingAttempts) via
    ``String.valueOf``; we reproduce that exactly.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str
    reason: str
    remaining_attempts: str
