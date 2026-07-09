"""SQLAlchemy model for the `verification_reports` table. Source: VerificationReport.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Double, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.outlet_application import OutletApplication


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # @OneToOne owning side — FK on this table, unique constraint
    outlet_application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("outlet_applications.id"),
        nullable=False,
        unique=True,
    )

    # FSSAI
    fssai_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fssai_registered_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fssai_expiry_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    fssai_name_match_score: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    # primitive boolean → NOT NULL
    fssai_name_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fssai_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # GSTIN
    gst_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    gst_business_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gst_name_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gst_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # PAN
    pan_format_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pan_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Bank / IFSC
    bank_ifsc_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_branch: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    bank_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Overall scoring
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # PENDING | PASSED | PARTIAL | FAILED
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    outlet_application: Mapped["OutletApplication"] = relationship(
        "OutletApplication",
        back_populates="verification_report",
    )
