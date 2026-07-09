"""
SQLAlchemy model for the `email_otp_tokens` table. Source: EmailOtpToken.java

This table is EXCLUSIVELY for email-verification OTPs (registration flow).
It must NEVER be shared with the pickup OTP system (spec §4.2).
"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EmailOtpToken(Base):
    __tablename__ = "email_otp_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(150), nullable=False)
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # primitive boolean — NOT NULL
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
