"""JWT generation & validation — direct port of Spring's JwtUtil.java.

Exact claim shape produced by generate_token() (mirrors Jwts.builder() in Java):
    {
      "sub": "<email>",                       # setSubject(email)
      "role": "<bare role name>",             # .claim("role", role) — NO "ROLE_" prefix
      "iat": <unix seconds>,                  # setIssuedAt(new Date())
      "exp": <unix seconds + TTL>             # setExpiration(...)
    }

The "ROLE_" prefix that Spring applied at SimpleGrantedAuthority level (in
JwtFilter.java) is an authority-layer concern; it is NOT present in the JWT
token itself in either the Java or the Python implementation.

Signing:
  - Algorithm: HS256 (SignatureAlgorithm.HS256 in Java).
  - Key: settings.JWT_SECRET passed as a raw str. python-jose accepts a str
    directly for HS256 and internally encodes it to bytes — this mirrors
    Java's `secret.getBytes()` (uses the platform default charset, which is
    UTF-8 on all modern JVMs and on Python here). Passing bytes vs str yields
    the same HMAC-SHA256 signature as long as the byte content matches.

TTL conversion:
  - settings.JWT_EXPIRY_MS is in milliseconds (matches application.yml's
    jwt.expiration: 86400000). python-jose's exp claim expects unix SECONDS,
    so we integer-divide by 1000 before adding to the iat timestamp.
"""
from __future__ import annotations

import time
from typing import Any

from jose import JWTError, jwt

from app.config import settings
from app.exceptions import ApiException

ALGORITHM = "HS256"


def generate_token(email: str, role: str) -> str:
    """Build and sign a JWT. Equivalent of JwtUtil.generateToken(email, role).

    The ``role`` argument is stored verbatim (e.g. "STUDENT", "ADMIN"). The
    "ROLE_" prefix is intentionally NOT added here — it was applied only at
    Spring Security's SimpleGrantedAuthority level in JwtFilter.java, never in
    the token, so the FastAPI-side token stays byte-for-byte compatible with
    tokens issued by the original Java service.
    """
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": email,
        "role": role,
        "iat": now,
        "exp": now + settings.JWT_EXPIRY_MS // 1000,
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Verify signature & expiry, return the full claims dict.

    Raises ApiException(401) on any JWT validation failure — mirroring how
    JwtFilter lets isTokenValid failures bubble up as 401 (the Spring
    authentication entry point rejects the request).
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ApiException("Invalid or expired token", 401) from exc


def extract_email(token: str) -> str:
    """Return the ``sub`` claim (the user's email). Mirrors jwtUtil.extractUsername."""
    return decode_token(token)["sub"]


def extract_role(token: str) -> str:
    """Return the bare ``role`` claim (no "ROLE_" prefix). Mirrors jwtUtil.extractRole."""
    return decode_token(token)["role"]


def is_token_valid(token: str) -> bool:
    """True iff the token is signature-valid and not expired.

    Direct port of JwtUtil.isTokenValid — catches every exception and returns
    a boolean so callers can branch without try/except.
    """
    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return True
    except Exception:
        return False
