"""Pydantic request/response schemas for the auth endpoints.

Mirrors the Java DTOs and Map<String, String> wire format produced by the
Spring Boot AuthController so the frontend contract (camelCase JSON, stringified
numbers) stays identical after the FastAPI migration.

Mirrored Java classes:
    - AuthRequest                 -> LoginRequest
    - RegisterRequest             -> RegisterRequest
    - VerifyEmailRequest          -> VerifyEmailRequest
    - ResendOtpRequest            -> ResendOtpRequest
    - AuthController (Map output) -> AuthResponse
    - AuthController message maps -> MessageResponse
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class LoginRequest(BaseModel):
    """Login payload.

    Mirrors Java AuthRequest: bare email/password strings with no bean
    validation constraints. Validation happens at the service layer.
    """

    email: str
    password: str


class RegisterRequest(BaseModel):
    """Registration payload.

    Mirrors Java RegisterRequest:
        - fullName: @NotBlank, max 120
        - email:    @Email, max 150
        - password: @Size(min=6)
        - otp:      frontend sends a blank "" at step 1; extra='ignore'
                    drops unknown/blank fields rather than 422-ing.
    Accepts camelCase input and allows population by python attribute name.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    full_name: str = Field(..., alias="fullName", max_length=120)
    email: EmailStr = Field(..., max_length=150)
    password: str = Field(..., min_length=6)


class VerifyEmailRequest(BaseModel):
    """OTP verification payload.

    Mirrors Java VerifyEmailRequest:
        - email: @Email
        - otp:   @Pattern(regexp = "\\d{6}") -> exactly six digits.
    """

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    otp: str = Field(..., pattern=r"^\d{6}$")


class ResendOtpRequest(BaseModel):
    """Resend-OTP payload.

    Mirrors Java ResendOtpRequest: just the email address.
    """

    email: str


class AuthResponse(BaseModel):
    """Auth success envelope.

    Mirrors the Map<String, String> returned by AuthController.login/register.
    Every value is a str (Java String.valueOf converts numbers/booleans),
    except the campus fields which are optional and absent when a user has no
    campus assignment (the Java code only does ``response.put("campusId", ...)``
    when ``user.getCampus() != null`` — we mirror that by excluding these
    fields from the serialized JSON when they are None).
    """

    # exclude_none=True so campusId/campusName are dropped when the user has
    # no campus — matching the Java conditional-put behaviour.
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        exclude_none=True,
    )

    token: str
    role: str
    name: str
    email: str
    id: str
    account_status: str = Field(..., alias="accountStatus")
    pending_penalty: str = Field(..., alias="pendingPenalty")
    no_show_count: str = Field(..., alias="noShowCount")
    campus_id: Optional[str] = Field(default=None, alias="campusId")
    campus_name: Optional[str] = Field(default=None, alias="campusName")


class MessageResponse(BaseModel):
    """Generic message envelope.

    Mirrors the simple {"message", "email", "status"} maps returned for
    resend-otp, verify, logout, etc. All fields except message are optional.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    message: str
    email: Optional[str] = None
    status: Optional[str] = None
