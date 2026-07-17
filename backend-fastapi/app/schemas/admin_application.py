"""Pydantic request/response schemas for the admin-application endpoints.

Mirrors the Java DTOs and the raw ``AdminApplication`` entity serialization
produced by Spring Boot's ``AdminApplicationController`` so the frontend
contract (camelCase JSON) stays identical after the FastAPI migration.

Mirrored Java classes:
    - AdminApplicationRequest                 -> AdminApplicationRequest
    - AdminApplicationReviewRequest           -> AdminApplicationReviewRequest
    - AdminApplication (raw entity response)  -> AdminApplicationResponse
    - (no DTO — Map<String, String> body)     -> AdminSendOtpRequest / AdminVerifyOtpRequest
    - (no DTO — Map<String, String>/<Object>) -> MessageResponse-like envelopes (reused inline)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

# Max size mirrors the Java @Size(max = 4_000_000) on idCardPhotoUrl. Pydantic
# enforces it at the schema layer the same way bean-validation did.
_MAX_PHOTO_CHARS = 4_000_000


class AdminSendOtpRequest(BaseModel):
    """Body for ``POST /api/admin-applications/send-otp``.

    Mirrors the raw ``Map<String, String>`` the Java controller read via
    ``body.getOrDefault("email", "")`` / ``body.getOrDefault("fullName", ...)``.
    Both fields are optional at the schema layer; the service does the blank
    check exactly as Java did (``email.isBlank() || !email.contains("@")``).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: Optional[str] = None
    full_name: Optional[str] = Field(default=None, alias="fullName")


class AdminVerifyOtpRequest(BaseModel):
    """Body for ``POST /api/admin-applications/verify-otp``.

    Mirrors the raw ``Map<String, String>`` body — ``email`` + ``otp``. Service
    does the same blank-check as Java.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: Optional[str] = None
    otp: Optional[str] = None


class AdminApplicationRequest(BaseModel):
    """Body for ``POST /api/admin-applications`` (public).

    Mirrors Java ``AdminApplicationRequest``:
        - fullName:       @NotBlank, max 120
        - applicantEmail: @Email, max 150
        - designation:    @NotBlank (TEXT — no upper bound at the column level,
                          spec §4.5)
        - idCardPhotoUrl: @NotBlank, @Size(max = 4_000_000)  ← base64 data-URI,
                          stored as TEXT (spec §4.5)
        - campusName:     @NotBlank, max 150
        - campusLocation: @NotBlank, max 200

    Note: ``campusEmailDomain`` is NOT collected from the client — derived
    server-side from ``applicantEmail`` (everything after '@'), exactly like
    the Java controller.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    full_name: str = Field(..., alias="fullName", min_length=1, max_length=120)
    applicant_email: EmailStr = Field(..., alias="applicantEmail", max_length=150)
    designation: str = Field(..., alias="designation", min_length=1)
    # Base64 data-URI of the campus ID card photo. Stored verbatim in a TEXT
    # column (spec §4.5) — the @Size cap is a payload guard, not a column width.
    id_card_photo_url: str = Field(
        ..., alias="idCardPhotoUrl", min_length=1, max_length=_MAX_PHOTO_CHARS
    )
    campus_name: str = Field(..., alias="campusName", min_length=1, max_length=150)
    campus_location: str = Field(
        ..., alias="campusLocation", min_length=1, max_length=200
    )


class AdminApplicationReviewRequest(BaseModel):
    """Body for ``PATCH /api/admin-applications/{id}/approve`` and ``/reject``.

    Mirrors Java ``AdminApplicationReviewRequest``:
        - message:           optional note to applicant (rejection reason or welcome)
        - temporaryPassword: required on approve, ignored on reject.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    message: Optional[str] = None
    temporary_password: Optional[str] = Field(default=None, alias="temporaryPassword")


# ── Response models ────────────────────────────────────────────────────────────


class _CampusRef(BaseModel):
    """Nested campus reference as serialized inside an admin application.

    Mirrors the JPA ``@ManyToOne createdCampus`` serialization shape — only the
    scalar campus fields, no recursion into users/outlets (which would be
    infinite and is not what the frontend consumes here).
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    name: str
    location: str
    email_domain: str = Field(..., alias="emailDomain")
    status: str


class AdminApplicationResponse(BaseModel):
    """Response envelope mirroring raw ``AdminApplication`` entity serialization.

    Reproduces the camelCase field names the frontend deserializes. The
    ``created_campus`` nested object is only present on APPROVED applications
    (Java serializes the ``createdCampus`` relationship when non-null); we use
    ``response_model_exclude_none`` at the route to drop it when null.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    full_name: str
    applicant_email: str
    designation: str
    id_card_photo_url: str
    campus_name: str
    campus_location: str
    campus_email_domain: str
    status: str
    rejection_reason: Optional[str] = None
    attempt_number: int
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    created_campus: Optional[_CampusRef] = None


class AdminOtpMessageResponse(BaseModel):
    """``{message}`` envelope for send-otp / verify-otp (Java Map<String,String>)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str
    verified: Optional[str] = None


class AdminApproveResponse(BaseModel):
    """``Map<String, Object>`` returned by PATCH /{id}/approve.

    Java returned ``{message, campusId, adminUserId}`` — ids are boxed Long,
    serialized as JSON numbers. We mirror that (ints, not stringified) since
    this path returned ``Map<String, Object>`` not ``Map<String, String>``.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str
    campus_id: int
    admin_user_id: int


class AdminRejectResponse(BaseModel):
    """``Map<String, String>`` returned by PATCH /{id}/reject.

    Java stringified every value (including remainingAttempts) via
    ``String.valueOf``; we reproduce that exactly.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str
    reason: str
    remaining_attempts: str
