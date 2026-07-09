"""SQLAlchemy model for the `outlet_payouts` table. Source: OutletPayout.java"""
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Date, DateTime, Double, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.outlet import Outlet


class OutletPayout(Base):
    __tablename__ = "outlet_payouts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("outlets.id"), nullable=False
    )

    # Online revenue (actual payout basis)
    gross_amount: Mapped[float] = mapped_column(Double, nullable=False)
    commission_rate: Mapped[float] = mapped_column(Double, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Double, nullable=False)
    net_amount: Mapped[float] = mapped_column(Double, nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # COD / Cash tracking — reporting only, no bank transfer
    cash_gross_amount: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)
    cash_order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # payout_XXXX from Razorpay X — null while PENDING or SIMULATED
    razorpay_payout_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # PENDING | SIMULATED | PROCESSING | PAID | FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Relationships
    outlet: Mapped["Outlet"] = relationship("Outlet", back_populates="payouts", lazy="joined")
