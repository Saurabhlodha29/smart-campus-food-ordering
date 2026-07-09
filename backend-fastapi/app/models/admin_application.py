"""SQLAlchemy model for the `admin_applications` table. Source: AdminApplication.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.campus import Campus


class AdminApplication(Base):
    __tablename__ = "admin_applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Applicant info
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    applicant_email: Mapped[str] = mapped_column(String(150), nullable=False)
    # columnDefinition = "TEXT"
    designation: Mapped[str] = mapped_column(Text, nullable=False)
    # Base64 data-URI of campus ID card — stored as TEXT (spec §4.5: not object storage)
    id_card_photo_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Campus being claimed
    campus_name: Mapped[str] = mapped_column(String(150), nullable=False)
    campus_location: Mapped[str] = mapped_column(String(200), nullable=False)
    campus_email_domain: Mapped[str] = mapped_column(String(100), nullable=False)

    # Review tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Set on APPROVED — reference to the auto-created campus
    created_campus_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("campuses.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    created_campus: Mapped[Optional["Campus"]] = relationship("Campus", lazy="joined")
