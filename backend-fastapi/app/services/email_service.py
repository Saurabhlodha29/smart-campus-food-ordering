"""
Email service — async SMTP send for email-verification OTPs.

Source of truth: EmailService.java (Spring Boot).

This service is EXCLUSIVELY for the EMAIL-VERIFICATION OTP system (registration
flow, DB-persisted, time-expiring tokens — see otp_service.py + EmailOtpToken).
It must NEVER be shared with the pickup OTP system, which is HMAC-derived and
never expires (spec §4.2).

FIRE-AND-FORGET SEMANTICS
-------------------------
The Java original annotated sendOtpEmail with @Async and swallowed
MessagingException (log, don't throw). A failed email therefore never crashes
the registration response; the user can retry via the resend endpoint.

We reproduce that here: otp_service.generate_and_send_otp awaits
send_otp_email directly (not via FastAPI BackgroundTasks), and every exception
inside this function is caught and logged — never re-raised. Direct await is
chosen over BackgroundTasks because Java's @Async dispatched the email BEFORE
the outer register transaction's throw — BackgroundTasks do not fire on
exception, which would drop the email in the duplicate-pending 409 path.

DEV / CI MODE
-------------
If MAIL_USERNAME is empty (no SMTP credentials configured) the function logs a
warning and returns immediately, matching the Java silent-failure behaviour.
This lets registration work end-to-end in dev/CI without a real Gmail account;
the OTP is still visible in the server logs via the DEBUG line in otp_service.
"""
from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


def _build_otp_email_html(full_name: str, otp_code: str) -> str:
    """
    Port of EmailService.buildOtpEmailHtml — identical HTML structure & inline
    styles so the rendered email looks exactly like the Spring Boot version.

    Layout: gradient header "SmartCampus", greeting with the user's full name,
    six digit-span boxes rendering the OTP, a 10-minute expiry note, an
    "if you didn't request this, ignore this email" line, and a footer.
    """
    digit_spans = "".join(
        '<span style="display:inline-block; width:48px; height:56px; '
        "line-height:56px; text-align:center; font-size:28px; font-weight:700; "
        "color:#1a1a2e; background:#f0f4ff; border:2px solid #d0d9ff; "
        'border-radius:8px; margin:0 4px;">' + c + "</span>"
        for c in otp_code
    )

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartCampus Verification Code</title>
</head>
<body style="margin:0; padding:0; background:#f4f4f7; font-family:'Segoe UI', Arial, sans-serif;">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#f4f4f7; padding:32px 0;">
<tr>
<td align="center">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 16px rgba(0,0,0,0.08);">
<tr>
<td style="background:linear-gradient(135deg,#667eea 0%%,#764ba2 100%%); padding:32px 40px; text-align:center;">
<h1 style="margin:0; color:#ffffff; font-size:24px; font-weight:700; letter-spacing:0.5px;">SmartCampus</h1>
</td>
</tr>
<tr>
<td style="padding:40px 40px 24px 40px;">
<p style="margin:0 0 8px 0; font-size:18px; font-weight:600; color:#1a1a2e;">Hi %s! Welcome to SmartCampus.</p>
<p style="margin:0 0 24px 0; font-size:15px; color:#444; line-height:1.6;">
Your verification code is:
</p>
<div style="text-align:center; margin:24px 0;">
%s
</div>
<p style="margin:24px 0 0 0; font-size:14px; color:#666; text-align:center;">
This code expires in <strong>10 minutes</strong>. Please do not share it with anyone.
</p>
</td>
</tr>
<tr>
<td style="padding:0 40px 32px 40px;">
<p style="margin:0; font-size:13px; color:#888; text-align:center; line-height:1.5;">
If you did not create an account, you can safely ignore this email.
</p>
</td>
</tr>
<tr>
<td style="padding:24px 40px; background:#fafafe; border-top:1px solid #eee;">
<p style="margin:0; font-size:12px; color:#999; text-align:center;">
&copy; SmartCampus. All rights reserved.
</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>""" % (full_name, digit_spans)


async def send_otp_email(to_email: str, full_name: str, otp_code: str) -> None:
    """
    Asynchronously send the email-verification OTP email via SMTP.

    Fire-and-forget: every exception is caught and logged so that a delivery
    failure never propagates to the caller (mirrors Java's
    `catch (MessagingException) -> log` over @Async). The user can retry via
    the resend-OTP endpoint.

    No-op when MAIL_USERNAME is unset — enables dev/CI without SMTP creds.
    """
    if not settings.MAIL_USERNAME:
        logger.warning(
            "MAIL_USERNAME not set — skipping OTP email send to %s", to_email
        )
        return

    html = _build_otp_email_html(full_name, otp_code)

    message = EmailMessage()
    message["From"] = settings.MAIL_USERNAME
    message["To"] = to_email
    message["Subject"] = "Your SmartCampus Verification Code: " + otp_code
    message.set_content(html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
        )
        logger.info("OTP email sent to %s", to_email)
    except Exception as e:  # noqa: BLE001 — intentional broad catch, see docstring
        logger.error("Failed to send OTP email to %s: %s", to_email, e)
        # Do NOT re-raise — fire-and-forget semantics (matches Java @Async + catch).
