"""Document Verification Service — port of ``DocumentVerificationService.java``.

WHAT IS PORTED (faithful to spec §4.11 + INTERVIEW_NOTES Module 2)
------------------------------------------------------------------
The Java original implemented a 3-layer free approach:

    Layer 1: Format validation (pure regex — instant, free)
    Layer 2: Public government / bank APIs
        - FoSCoS FSSAI public search (free, no key)
        - GSTN public taxpayer API (free, no key)
        - Razorpay IFSC public API (free, no key)
    Layer 3: Name cross-matching (own string logic, free)

Per the migration task prompt and spec §4.11 ("format-only, no live government
API call" — explicitly out of scope), THIS PORT IMPLEMENTS LAYER 1 ONLY.
Layers 2 and 3 are NOT wired: every layer-2 lookup returns its existing
"API unavailable → format-only" degraded result (the same graceful-degradation
branch the Java original already had for when those endpoints were unreachable).
This means:

  - The orchestration shape (create PENDING report → run each verification
    step → compute overall score → mark report done) is ported verbatim.
  - The scoring formula (FSSAI=40/10, GST=30/8, PAN=15, IFSC=15) is ported
    verbatim, so a fully-valid set of document formats still scores 33 (10+8+15)
    instead of 100 — exactly as it would in Java when all three APIs were
    unreachable. The admin sees a PARTIAL/FAILED report and reviews manually,
    which is the documented behaviour.
  - The entity shape (``VerificationReport`` columns) is preserved so a real
    verification API can be dropped in later without changing the workflow
    around it (INTERVIEW_NOTES Module 2: "the architecture is specifically
    designed so a real verification API can be dropped in later").

ASYNC vs SYNCHRONOUS (DIVERGENCE FLAGGED)
----------------------------------------
Java: ``verifyApplicationAsync`` was ``@Async @Transactional`` — the controller
returned the saved application immediately, then a background thread created
the PENDING report row and populated it in its own transaction. The campus
admin saw ``status=PENDING`` for a few seconds until the report completed.

Python port: verification runs **synchronously** within the submit request,
in the same transaction as the application save. The report is fully populated
by the time the submit response is returned. This is a documented divergence
flagged in migration-notes/03-applications.md:

  - PRO: deterministic for tests; admin never sees a half-PENDING report;
    simpler than wiring asyncio task dispatch + a separate session.
  - CON: adds the (tiny, regex-only) verification latency to the submit
    response time.

The latency is negligible (pure regex, no I/O) — the divergence is a
simplification, not a behavior change. If real Layer-2 APIs are ever added
later, this is the spot to revisit (use FastAPI ``BackgroundTasks`` or an
asyncio task with its own session).

TRANSACTION MODEL
-----------------
``verify_application`` uses ``db.flush()`` only — the caller owns the commit.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outlet_application import OutletApplication
from app.models.verification_report import VerificationReport
from app.services import document_format_validator as fv

logger = logging.getLogger(__name__)


# ── Status constants (parity with VerificationReport.java) ────────────────────
STATUS_PENDING = "PENDING"
STATUS_PASSED = "PASSED"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAILED = "FAILED"


async def verify_application(app: OutletApplication, db: AsyncSession) -> VerificationReport:
    """Run Layer-1 document verification for an outlet application.

    Creates a PENDING report row, runs each format check, computes the overall
    score, marks the report completed, flushes — and returns the report. The
    caller owns the commit (same transaction as the application save).

    Any unexpected error is caught and marks the report FAILED with a note,
    exactly like the Java ``runVerification`` catch-all that set the report to
    FAILED and persisted ``"Verification engine error: " + e.getMessage()``.
    """
    # Create the report row immediately so even a partial run leaves a
    # persisted PENDING/FAILED row — parity with Java's
    # ``report = reportRepo.save(new VerificationReport(app))`` before the try.
    report = VerificationReport(
        outlet_application=app,
        fssai_name_mismatch=False,
        gst_name_mismatch=False,
        pan_format_valid=False,
        overall_score=0,
        overall_status=STATUS_PENDING,
        created_at=datetime.now(),
    )
    db.add(report)
    await db.flush()  # populate report.id; keep going inside the same transaction

    try:
        _run_verification(app, report)
    except Exception as e:  # noqa: BLE001 — parity with Java's catch-all
        # Mark the report FAILED so the admin sees something went wrong and
        # can review manually. Mirrors Java's catch-all in verifyApplicationAsync.
        logger.exception(
            "[DocVerify] Unexpected error verifying application id=%s", app.id
        )
        report.overall_status = STATUS_FAILED
        report.fssai_note = f"Verification engine error: {e}"
        report.completed_at = datetime.now()

    await db.flush()
    logger.info(
        "[DocVerify] Completed for application id=%s. Score=%s Status=%s",
        app.id, report.overall_score, report.overall_status,
    )
    return report


def _run_verification(app: OutletApplication, report: VerificationReport) -> None:
    """Populate ``report`` in place with each document's format-only result.

    This is a direct port of ``DocumentVerificationService.runVerification``,
    with the Layer-2 API calls replaced by their existing "API unavailable"
    graceful-degradation branches (spec §4.11: no live government API).

    Scoring (out of 100, ported verbatim):
        FSSAI API-verified → 40 pts (format-only → 10 pts)
        GSTIN API-verified → 30 pts (format-only → 8 pts)
        PAN format valid   → 15 pts
        IFSC API-verified  → 15 pts (format-only → 0 pts — the Java IFSC
                                       branch only credited a real API result)

    The Java IFSC branch credited 15 only when ``bankIfscValid == true`` (the
    real Razorpay lookup) — there was no "format-only → fewer points" fallback
    there. We preserve that asymmetry.
    """
    # ── 1. FSSAI ──────────────────────────────────────────────────────────────
    fssai_num = app.fssai_license_number
    fssai_format_ok = fssai_num is not None and fv.validate_fssai_format(fssai_num)

    if not fssai_format_ok:
        report.fssai_verified = False
        report.fssai_note = (
            "FSSAI number not provided"
            if fssai_num is None
            else fv.get_fssai_format_error(fssai_num)
        )
    else:
        # Layer 2 (FoSCoS) deliberately not wired per spec §4.11. Use the
        # exact "API unavailable" graceful-degradation branch the Java original
        # had for unreachable FoSCoS.
        report.fssai_verified = None
        report.fssai_note = (
            "FoSCoS portal unreachable — format validated only. "
            "Manual verification recommended."
        )

    # ── 2. GSTIN ──────────────────────────────────────────────────────────────
    gstin = app.gstin
    gst_format_ok = gstin is not None and fv.validate_gstin_format(gstin)

    if not gst_format_ok:
        report.gst_verified = False
        report.gst_note = (
            "GSTIN not provided" if gstin is None else fv.get_gstin_format_error(gstin)
        )
    else:
        # Layer 2 (GSTN) deliberately not wired per spec §4.11.
        report.gst_verified = None
        report.gst_note = (
            "GSTN portal unreachable — format validated only. "
            "Manual verification recommended."
        )

    # ── 3. PAN ────────────────────────────────────────────────────────────────
    # No free real-time API for PAN in Java either — format validation only.
    pan = app.pan_number
    pan_format_ok = pan is not None and fv.validate_pan_format(pan)
    report.pan_format_valid = pan_format_ok
    if pan is None:
        report.pan_note = "PAN not provided"
    elif pan_format_ok:
        report.pan_note = "Format valid (real-time PAN verification requires paid API)"
    else:
        report.pan_note = (
            "Invalid PAN format — expected 5 letters + 4 digits + 1 letter "
            "(e.g. ABCDE1234F)"
        )

    # ── 4. Bank / IFSC ────────────────────────────────────────────────────────
    ifsc = app.bank_ifsc_code
    ifsc_format_ok = ifsc is not None and fv.validate_ifsc_format(ifsc)

    if not ifsc_format_ok:
        report.bank_ifsc_valid = False
        report.bank_note = (
            "IFSC code not provided"
            if ifsc is None
            else "Invalid IFSC format — expected 4 letters + 0 + 6 alphanumeric "
                 "(e.g. SBIN0001234)"
        )
    else:
        # Layer 2 (Razorpay IFSC) deliberately not wired per spec §4.11.
        report.bank_ifsc_valid = None
        report.bank_note = "IFSC API temporarily unavailable — format validated only"

    # Account number format (no API for this in Java either)
    acc_no = app.bank_account_number
    if acc_no is not None and not fv.validate_account_number_format(acc_no):
        existing = report.bank_note
        report.bank_note = (
            (existing + " | " if existing else "")
            + "Account number format invalid (expected 9–18 digits)"
        )

    # ── 5. Compute overall score ──────────────────────────────────────────────
    score = 0

    # FSSAI: 40 if API-verified, else 10 if format OK (parity with Java).
    if report.fssai_verified is True:
        score += 40
    elif fssai_format_ok:
        score += 10

    # GST: 30 if API-verified, else 8 if format OK (parity with Java).
    if report.gst_verified is True:
        score += 30
    elif gst_format_ok:
        score += 8

    # PAN: 15 if format valid (no API path exists in Java either).
    if report.pan_format_valid:
        score += 15

    # IFSC: 15 only if API-verified true (Java credited no fallback points here).
    if report.bank_ifsc_valid is True:
        score += 15

    report.overall_score = score
    if score >= 80:
        report.overall_status = STATUS_PASSED
    elif score >= 50:
        report.overall_status = STATUS_PARTIAL
    else:
        report.overall_status = STATUS_FAILED
    report.completed_at = datetime.now()
