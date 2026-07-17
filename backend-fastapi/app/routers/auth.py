"""Auth router — /api/auth/* endpoints.

Source of truth: AuthController.java (Spring Boot @RestController @RequestMapping("/api/auth")).

All four endpoints are PUBLIC (no JWT required) — matches SecurityConfig.java's
`.requestMatchers("/api/auth/**").permitAll()`. Auth dependencies (get_current_user,
require_role) are NOT used here; they're wired into protected routers in later modules.

The router is thin: it parses + validates the Pydantic request model, delegates to the
service layer, and wraps the dict[str, str] result in the appropriate Pydantic response
model. No business logic lives in the handler bodies (per MIGRATION_RULES §6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendOtpRequest,
    VerifyEmailRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse, response_model_exclude_none=True)
async def login(
    request: LoginRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Authenticate a user and return a JWT + profile envelope.

    Mirrors AuthController.login — all values are stringified in the service
    (matching Java String.valueOf) so AuthResponse validates cleanly.

    ``response_model_exclude_none=True`` drops campusId/campusName from the
    JSON when the user has no campus — matching Java's
    ``if (user.getCampus() != null) response.put(...)`` conditional-put.
    """
    result = await auth_service.login(request.email, request.password, db)
    await db.commit()
    return AuthResponse(**result)


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Register a new student and email OTP. No JWT yet (PENDING_VERIFICATION).

    Mirrors AuthController.register — @ResponseStatus(HttpStatus.CREATED).
    Returns 201 with a {message, email, status} envelope (no token issued).
    A 409 for a duplicate pending account still triggers a 201-worthy
    regeneration behind the scenes but raises ApiException, so FastAPI will
    short-circuit to the error handler rather than this 201 path.
    """
    result = await auth_service.register(
        request.full_name, request.email, request.password, db
    )
    await db.commit()
    return MessageResponse(**result)


@router.post(
    "/verify-email",
    response_model=AuthResponse,
    response_model_exclude_none=True,
)
async def verify_email(
    request: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Validate the OTP emailed at registration (PENDING_VERIFICATION).
    On success the account is activated and a JWT is issued — same shape as /login.
    """
    result = await auth_service.verify_email(request.email, request.otp, db)
    await db.commit()
    return AuthResponse(**result)


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    request: ResendOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Re-issue and email a fresh OTP for an account still in PENDING_VERIFICATION."""
    result = await auth_service.resend_otp(request.email, db)
    await db.commit()
    return MessageResponse(**result)
