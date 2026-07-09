"""SQLAlchemy model for the `outlets` table. Source: Outlet.java"""
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.campus import Campus
    from app.models.user import User
    from app.models.menu_item import MenuItem
    from app.models.pickup_slot import PickupSlot
    from app.models.order import Order
    from app.models.outlet_payout import OutletPayout
    from app.models.outlet_rating import OutletRating


class Outlet(Base):
    __tablename__ = "outlets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    campus_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("campuses.id"), nullable=False
    )
    manager_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )

    # PENDING_LAUNCH | ACTIVE | CLOSED | SUSPENDED | DELETED
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    avg_prep_time: Mapped[int] = mapped_column(nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Null means no time restriction — manual toggle only
    opening_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    closing_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Payout / bank details
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bank_ifsc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    bank_account_holder_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    razorpay_fund_account_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    razorpay_contact_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    campus: Mapped["Campus"] = relationship("Campus", back_populates="outlets", lazy="joined")
    manager: Mapped["User"] = relationship(
        "User", back_populates="managed_outlets", foreign_keys=[manager_id], lazy="joined"
    )
    menu_items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="outlet")
    pickup_slots: Mapped[list["PickupSlot"]] = relationship("PickupSlot", back_populates="outlet")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="outlet")
    payouts: Mapped[list["OutletPayout"]] = relationship("OutletPayout", back_populates="outlet")
    ratings: Mapped[list["OutletRating"]] = relationship(
        "OutletRating", back_populates="outlet", foreign_keys="OutletRating.outlet_id"
    )
