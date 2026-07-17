"""
Auth service — business logic for the /api/auth/* endpoints.

Source of truth: AuthController.java (Spring Boot). This module is the
pure-business-logic layer; it receives already-parsed primitive arguments
from the router (no Pydantic request models here) and returns plain
dict[str, str] envelopes that the router then validates against the Pydantic
response schema. This split mirrors Spring's @Service/@Controller separation.

TRANSACTION MODEL
-----------------
Every mutating function uses `db.flush()` only — the router (FastAPI dependency
that owns the AsyncSession) commits on success and rolls back on exception.
This reproduces the Spring @Transactional boundary that lived on the controller
methods: a failure after any side-effect (e.g. after OTP regeneration) leaves
the session in a state the caller discards.

WHY dict[str, str] AND NOT AuthResponse
----------------------------------------
The Java controller returned Map<String, String> and used String.valueOf for
every scalar (ids, penalty, no-show count, campus id). To keep the wire format
byte-identical we reproduce that here — every value is a str — and let the
router wrap the dict in AuthResponse/MessageResponse only for documentation
and alias validation. Numbers are NEVER sent as JSON numbers.

EAGER LOADING
-------------
User.role is lazy="joined" so it auto-loads with no explicit option needed.
User.campus is lazy="select", which in async SQLAlchemy raises
MissingGreenlet if accessed without an explicit eager load — so every user
query that may read user.campus uses joinedload(User.campus). This matches the
Hibernate side where campus was a lazy @ManyToOne that got touched only when
serialized in the response.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.exceptions import ApiException
from app.models.campus import Campus
from app.models.role import Role
from app.models.user import User
from app.security.jwt import generate_token
from app.security.password import hash_password, verify_password
from app.services.otp_service import generate_and_send_otp, validate_otp


def _build_auth_response(user: User, token: str, account_status: str) -> dict[str, str]:
    """Build the camelCase Map<String, String> auth envelope from a User.

    Reproduces the literal put(...) calls in AuthController.login / verifyEmail.
    The caller passes the explicit ``account_status`` to use — for login it is
    the user's current status; for verify-email the Java code hard-coded the
    string "ACTIVE" rather than re-reading the entity, and we do the same.

    Assumes ``user.role`` (lazy="joined", always loaded) and ``user.campus``
    (eager-loaded by the caller via joinedload) are already populated, so no
    lazy-load happens inside the response builder.
    """
    response: dict[str, str] = {
        "token": token,
        "role": user.role.name,
        "name": user.full_name,
        "email": user.email,
        "id": str(user.id),
        "accountStatus": account_status,
        "pendingPenalty": str(user.pending_penalty_amount),
        "noShowCount": str(user.no_show_count),
    }
    # Java parity: only put campusId/campusName when user.getCampus() is non-null.
    # This keeps them ABSENT from the JSON (not present-with-null) — matches the
    # original wire format exactly.
    if user.campus is not None:
        response["campusId"] = str(user.campus.id)
        response["campusName"] = user.campus.name
    return response


async def login(email: str, password: str, db: AsyncSession) -> dict[str, str]:
    """Authenticate a user and return the auth envelope + JWT.

    Port of AuthController.login. The status ladder is preserved exactly:
      1. unknown email            -> 401 "Invalid email or password"
      2. wrong password           -> 401 "Invalid email or password"
                                     (same message — no user enumeration leak)
      3. PENDING_VERIFICATION      -> 403 with the OTP-friendly message
      4. any non-ACTIVE status     -> 403 generic "account is <status>"
      5. ACTIVE                   -> success

    Campus is eager-loaded via joinedload because User.campus is lazy="select"
    and async sessions cannot lazy-load on attribute access.
    """
    stmt = (
        select(User)
        .options(joinedload(User.campus))
        .where(User.email == email)
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise ApiException("Invalid email or password", 401)

    if not verify_password(password, user.password_hash):
        raise ApiException("Invalid email or password", 401)

    if user.account_status == "PENDING_VERIFICATION":
        raise ApiException(
            "Email not verified. Please check your inbox for the OTP, "
            "or use /api/auth/resend-otp to get a new one.",
            403,
        )

    if user.account_status != "ACTIVE":
        raise ApiException(
            "Your account is " + user.account_status + ". Please contact support.",
            403,
        )

    token = generate_token(user.email, user.role.name)
    return _build_auth_response(user, token, user.account_status)


async def register(
    full_name: str,
    email: str,
    password: str,
    db: AsyncSession,
) -> dict[str, str]:
    """Register a new student, look up campus by email domain, send OTP.

    Port of AuthController.register (@ResponseStatus CREATED — the router sets
    the 201 status code; this function just returns the message map).

    Domain -> Campus resolution: the substring of the email after '@' is matched
    against Campus.email_domain. Spring used campusRepo.findByEmailDomain which
    returned an Optional; we use a scalar_one_or_none() on an email_domain
    equality filter — there's a UNIQUE-ish expectation here (in practice
    domains are unique per campus).

    Duplicate-email flow preserves the Java parity choice: if the existing
    account is still pending verification we DON'T reject outright — we
    regenerate + resend an OTP (re-using the existing account) and then raise
    409 with a helpful message. This lets a user who abandoned registration
    mid-flow resume cleanly.
    """
    email = email.lower().strip()

    # Look up existing user eagerly loading campus — the branch below never
    # actually reads campus, but loading it keeps the entity fully populated
    # and matches the Spring side which did userRepo.findByEmail (full entity).
    existing_stmt = (
        select(User)
        .options(joinedload(User.campus))
        .where(User.email == email)
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        if existing.account_status == "PENDING_VERIFICATION":
            # Regenerate OTP on the existing pending account and warn the user.
            # flush() persists the OTP-service side-effects (token row delete +
            # insert) before raising so the resend actually sticks if the caller
            # catches and inspects — though the router lets the exception undo
            # the whole thing; the Spring behaviour is the same (@Transactional
            # rollback on throw).
            await generate_and_send_otp(email, existing.full_name, db)
            await db.flush()
            raise ApiException(
                "Account already exists but email is not verified. "
                "A new OTP has been sent to " + email + ".",
                409,
            )
        raise ApiException("An account with this email already exists.", 409)

    domain = email[email.index("@") + 1:]

    campus_stmt = select(Campus).where(Campus.email_domain == domain)
    campus = (await db.execute(campus_stmt)).scalar_one_or_none()
    if campus is None:
        raise ApiException(
            "No registered campus found for email domain '@" + domain + "'. "
            "Your campus may not be on the platform yet.",
            404,
        )

    if campus.status != "ACTIVE":
        raise ApiException(
            "The campus for your email domain is not currently active.", 403
        )

    student_role = (
        await db.execute(select(Role).where(Role.name == "STUDENT"))
    ).scalar_one_or_none()
    if student_role is None:
        raise ApiException("STUDENT role not seeded — contact support.", 500)

    # Link via the relationship objects — SQLAlchemy 2.0 populates the role_id
    # / campus_id FK columns from the assigned objects on flush. Equivalent to
    # the Java `new User(fullName, email, passwordEncoder.encode(password),
    # studentRole, campus)`.
    student = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=student_role,
        campus=campus,
        is_active=True,
        no_show_count=0,
        pending_penalty_amount=0.0,
        account_status="PENDING_VERIFICATION",
        created_at=datetime.now(),
    )
    db.add(student)
    await db.flush()  # populates student.id; caller commits

    await generate_and_send_otp(email, full_name, db)

    return {
        "message": "Registration successful! Please check " + email + " for your 6-digit OTP.",
        "email": email,
        "status": "PENDING_VERIFICATION",
    }


async def verify_email(email: str, otp: str, db: AsyncSession) -> dict[str, str]:
    """Validate a registration OTP and activate the account.

    Port of AuthController.verifyEmail. No email is sent on success (the Java
    controller doesn't either).

    On success the account_status is flipped to "ACTIVE" and an auth envelope
    with a freshly minted JWT is returned, exactly like login — the Java
    controller did the same so the frontend could transition straight into the
    logged-in state without a second round-trip.
    """
    email = email.lower().strip()

    stmt = (
        select(User)
        .options(joinedload(User.campus))
        .where(User.email == email)
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise ApiException("No account found for this email.", 404)

    if user.account_status != "PENDING_VERIFICATION":
        if user.account_status == "ACTIVE":
            raise ApiException("Email is already verified. Please log in.", 400)
        raise ApiException(
            "Account cannot be verified in its current state. Contact support.", 403
        )

    await validate_otp(email, otp, db)

    user.account_status = "ACTIVE"
    await db.flush()

    token = generate_token(user.email, user.role.name)
    # Java hard-coded "ACTIVE" into the response map here rather than
    # re-reading user.getAccountStatus(); we do the same for parity.
    return _build_auth_response(user, token, "ACTIVE")


async def resend_otp(email: str, db: AsyncSession) -> dict[str, str]:
    """Resend a fresh OTP to a still-pending account.

    Port of AuthController.resendOtp. The Java method received a raw
    Map<String,String> body and did its own blank-check; here the Pydantic
    ResendOtpRequest schema enforces that an email is present, but we still
    reproduce the blank check for exact parity and to harden against any
    future schema relaxation (e.g. if the field becomes optional).
    """
    email = email.lower().strip()

    if email == "":
        raise ApiException("Email is required.", 400)

    # No joinedload needed — resend never reads user.campus.
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        raise ApiException("No account found for this email.", 404)

    if user.account_status != "PENDING_VERIFICATION":
        raise ApiException("This account does not need OTP verification.", 400)

    await generate_and_send_otp(email, user.full_name, db)

    return {"message": "A new OTP has been sent to " + email + "."}
