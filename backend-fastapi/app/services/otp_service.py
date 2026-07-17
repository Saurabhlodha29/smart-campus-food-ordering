"""
OTP service — email-verification OTP (registration flow).

Source of truth: OtpService.java (Spring Boot).

TWO-OTP-SYSTEMS SEPARATION (spec §4.2)
-------------------------------------
This service governs the EMAIL-VERIFICATION OTP ONLY:
  - DB-persisted (email_otp_tokens table)
  - Time-expiring (OTP_EXPIRY_MINUTES, default 10)
  - Single-use (marked used=True on successful verify)
  - Generated randomly with secrets.randbelow (cryptographic, like SecureRandom)

It is COMPLETELY SEPARATE from the PICKUP OTP system, which is:
  - HMAC-derived from a shared secret + order id (never stored in a table)
  - Non-expiring (valid until the order is picked up)
  - Recomputed on verification, never compared from DB

Do NOT share tables, secrets, config variables, or methods between the two.
OTP_SECRET is for the pickup HMAC; OTP_EXPIRY_MINUTES is for this email-verify
system only.

LITERAL-STRING-COMPARE VERIFICATION
-----------------------------------
Verification compares the submitted OTP string directly against the stored
otp_code string (`token.otp_code != submitted_otp`), exactly like the Java
original (`token.getOtpCode().equals(submittedOtp)`). It is NEVER a hash or
HMAC recompute — those belong to the pickup OTP, not here. Keeping it a literal
compare is a deliberate security/parity choice: the token is already a random
6-digit secret stored in the DB, and recomputing would add nothing.

TRANSACTION MODEL
----------------
All mutating methods use `db.flush()` only — the caller owns the commit. This
matches the Spring @Transactional boundary (OtpService → AuthController/Repo).
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select, delete

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import ApiException
from app.models.email_otp_token import EmailOtpToken
from app.services.email_service import send_otp_email

logger = logging.getLogger(__name__)


async def generate_and_send_otp(
    email: str, full_name: str, db: AsyncSession
) -> None:
    """Invalidate previous tokens, generate a fresh 6-digit OTP, persist it,
    and send the email.

    FIRE-AND-FORGET SEMANTIC (mirrors Java's @Async sendOtpEmail)
    -----------------------------------------------------------
    The email send is awaited directly rather than queued via FastAPI's
    BackgroundTasks. This is intentional and more faithful to Java than
    BackgroundTasks: Java's @Async sent the email BEFORE the outer register
    transaction's throw, so the user received the OTP even when register
    raised 409 (duplicate-pending case). FastAPI's BackgroundTasks do NOT fire
    on exception, which would drop the email — a divergence. Direct await
    preserves the Java behavior because send_otp_email swallows all errors
    internally (it never propagates).
    """
    # Delete all existing tokens for this email (matches otpTokenRepo.deleteAllByEmail)
    await db.execute(delete(EmailOtpToken).where(EmailOtpToken.email == email))

    # Cryptographically-secure 6-digit code, equivalent to Java's
    # SecureRandom.nextInt(1_000_000) formatted with String.format("%06d", ...)
    otp = f"{secrets.randbelow(1_000_000):06d}"

    # Naive local datetime matches Hibernate's LocalDateTime.now() as stored in
    # the DB (email_otp_tokens.created_at / expires_at are naive DateTime cols).
    now = datetime.now()
    expires_at = now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    token = EmailOtpToken(
        email=email,
        otp_code=otp,
        expires_at=expires_at,
        used=False,
        created_at=now,
    )
    db.add(token)
    await db.flush()  # populate auto-generated id; caller commits

    # Preserve the exact debug line from Java — lets tests read the OTP from
    # logs even when email delivery is mocked/skipped in dev/CI.
    print(f"DEBUG OTP GENERATED: {otp}")

    # Send the email directly (await). send_otp_email swallows all errors so
    # this never prevents a 409/500 from reaching the caller — mirrors Java's
    # @Async catch-MessagingException-and-log semantics.
    await send_otp_email(email, full_name, otp)


async def validate_otp(email: str, submitted_otp: str, db: AsyncSession) -> None:
    """
    Validate a submitted OTP against the latest valid (unused, unexpired) token
    for this email. On success marks the token used.

    Raises ApiException(400) if no valid token exists or the OTP doesn't match.

    Verification is a LITERAL STRING COMPARE (token.otp_code != submitted_tp),
    intentionally NOT a hash/recompute — see module docstring.
    """
    stmt = (
        select(EmailOtpToken)
        .where(
            EmailOtpToken.email == email,
            EmailOtpToken.used == False,  # noqa: E712 — SQLAlchemy filter idiom
            EmailOtpToken.expires_at > datetime.now(),
        )
        .order_by(EmailOtpToken.created_at.desc())
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()

    if not tokens:
        raise ApiException(
            "OTP expired or not found. Please request a new one.", 400
        )

    token = tokens[0]  # latest valid token (first in DESC order)

    # Literal string compare — never a recompute. See module docstring.
    if token.otp_code != submitted_otp:
        raise ApiException("Invalid OTP. Please check and try again.", 400)

    # Mark the token as used (mirrors token.markUsed() in Java)
    token.used = True
    await db.flush()  # caller commits


async def is_email_verified(email: str, db: AsyncSession) -> bool:
    """
    Return True if any previously-used (verified) OTP token exists for this
    email, False otherwise.

    Mirrors Java's `otpTokenRepo.existsByEmailAndUsedTrue(email)`. Included for
    parity with the Spring service; AuthController endpoints don't call it today
    but public application flows may.
    """
    stmt = (
        select(EmailOtpToken)
        .where(
            EmailOtpToken.email == email,
            EmailOtpToken.used == True,  # noqa: E712 — SQLAlchemy filter idiom
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None
 