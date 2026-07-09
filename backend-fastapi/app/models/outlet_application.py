"""SQLAlchemy model for the `outlet_applications` table. Source: OutletApplication.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.campus import Campus
    from app.models.outlet import Outlet
    from app.models.verification_report import VerificationReport


class OutletApplication(Base):
    __tablename__ = "outlet_applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Manager / applicant info
    manager_name: Mapped[str] = mapped_column(String(120), nullable=False)
    manager_email: Mapped[str] = mapped_column(String(150), nullable=False)

    # Outlet info
    outlet_name: Mapped[str] = mapped_column(String(150), nullable=False)
    outlet_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avg_prep_time: Mapped[int] = mapped_column(Integer, nullable=False)
    # Base64 license document — TEXT (spec §4.5)
    license_doc_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Base64 outlet photo — TEXT (spec §4.5)
    outlet_photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Document verification fields
    fssai_license_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pan_number: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    bank_ifsc_code: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)

    campus_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("campuses.id"), nullable=False
    )

    # Review tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Set on APPROVED — reference to the auto-created outlet
    created_outlet_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("outlets.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    campus: Mapped["Campus"] = relationship("Campus", lazy="joined")
    created_outlet: Mapped[Optional["Outlet"]] = relationship(
        "Outlet", foreign_keys=[created_outlet_id], lazy="select"
    )
    # mappedBy = "outletApplication" in Java — FK is on VerificationReport side
    verification_report: Mapped[Optional["VerificationReport"]] = relationship(
        "VerificationReport",
        back_populates="outlet_application",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )
