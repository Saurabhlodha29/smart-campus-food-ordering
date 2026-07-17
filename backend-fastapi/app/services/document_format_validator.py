"""Layer 1 of the 3-layer document verification system.

Direct, faithful port of ``DocumentFormatValidator.java`` (Spring Boot
``@Component``). Validates Indian government / bank document number formats
using pure regex — completely free, instant, no external API calls.

Catches:
  - Mistyped numbers
  - Fake / randomly generated numbers (wrong length or character pattern)
  - Wrong document submitted in the wrong field

Format rules are based on the official government-issued document
specifications, exactly as in the Java original.

WHAT IS AND IS NOT PORTED HERE (spec §4.11 + INTERVIEW_NOTES Module 2)
---------------------------------------------------------------------
THIS MODULE IS PORTED VERBATIM — it is pure format validation (Layer 1), no
network calls, and the migration spec (§4.11) explicitly says to preserve
format-only validation as-is.

Layers 2 and 3 of the original Java verification (the live government-API
calls to FoSCoS / GSTN / Razorpay IFSC, and the name cross-matching) are
explicitly OUT OF SCOPE for this migration per the prompt (do not wire a live
government API) and per spec §4.11 ("India-specific formats are hardcoded,
not configuration ... format-only, no live government API call"). The
``document_verification_service`` module ports the orchestration around
Layer 1 but downgrades Layers 2/3 to "API unavailable → format-only" results
— which is exactly the graceful-degradation branch the Java original already
had for when those APIs were unreachable.
"""
from __future__ import annotations

import re

# ── Regex patterns (verbatim from Java) ────────────────────────────────────────
# FSSAI Food Business Operator license number: exactly 14 digits.
_FSSAI_RE = re.compile(r"^\d{14}$")

# GST Identification Number: 15 chars — 2-digit state, 5 letters, 4 digits,
# 1 letter, 1 entity char (1-9 or A-Z), literal 'Z', 1 checksum (digit/letter).
_GSTIN_RE = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

# Permanent Account Number: 5 uppercase letters + 4 digits + 1 uppercase letter.
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")

# IFSC (Indian Financial System Code): 4 letters + '0' + 6 alphanumeric.
# The 5th char is always '0' — mandated RBI format rule.
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")

# Indian bank account number: 9–18 digits (covers all scheduled banks).
_ACCOUNT_RE = re.compile(r"^\d{9,18}$")


def validate_fssai_format(number: str | None) -> bool:
    """FSSAI Food Business Operator license number — exactly 14 digits.

    Example: ``10020011004823``
    """
    return number is not None and bool(_FSSAI_RE.match(number))


def validate_gstin_format(gstin: str | None) -> bool:
    """GST Identification Number — 15 chars per the official format spec.

    Example: ``29ABCDE1234F1Z5``
    """
    return gstin is not None and bool(_GSTIN_RE.match(gstin))


def validate_pan_format(pan: str | None) -> bool:
    """Permanent Account Number — 5 letters + 4 digits + 1 letter.

    The 4th letter encodes taxpayer type (P=individual, C=company, ...) but
    we don't validate that here — format check is sufficient for Layer 1
    (matches Java parity).

    Example: ``ABCDE1234F``
    """
    return pan is not None and bool(_PAN_RE.match(pan))


def validate_ifsc_format(ifsc: str | None) -> bool:
    """IFSC (Indian Financial System Code) — 4 letters + '0' + 6 alphanumeric.

    The 5th character is always zero — a mandated RBI format rule.

    Example: ``SBIN0001234``
    """
    return ifsc is not None and bool(_IFSC_RE.match(ifsc))


def validate_account_number_format(account_no: str | None) -> bool:
    """Indian bank account number — 9–18 digits (covers all scheduled banks).

    - SBI: 11 digits
    - HDFC: 14 digits
    - ICICI: 12 digits
    """
    return account_no is not None and bool(_ACCOUNT_RE.match(account_no))


# ── Human-readable error-message helpers (parity with Java getXxxFormatError) ──
# These mirror the convenience methods on the Java validator that returned a
# human-readable reason for failure (or None if valid). They are consumed by
# the document verification service when populating the report's note fields.


def get_fssai_format_error(number: str | None) -> str | None:
    """Return a human-readable error string for an invalid FSSAI number, or None if valid."""
    if number is None or number.strip() == "":
        return "FSSAI license number is required"
    if not re.match(r"^\d+$", number):
        return "FSSAI number must contain digits only"
    if len(number) != 14:
        return f"FSSAI number must be exactly 14 digits (got {len(number)})"
    return None  # valid


def get_gstin_format_error(gstin: str | None) -> str | None:
    """Return a human-readable error string for an invalid GSTIN, or None if valid."""
    if gstin is None or gstin.strip() == "":
        return "GSTIN is required"
    if len(gstin) != 15:
        return f"GSTIN must be exactly 15 characters (got {len(gstin)})"
    if not validate_gstin_format(gstin):
        return (
            "GSTIN format is invalid. Expected: 2-digit state + 5 letters + 4 digits "
            "+ letter + digit + Z + checksum"
        )
    return None
