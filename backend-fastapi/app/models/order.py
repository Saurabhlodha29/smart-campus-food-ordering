"""SQLAlchemy model for the `orders` table. Source: Order.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.outlet import Outlet
    from app.models.pickup_slot import PickupSlot
    from app.models.order_item import OrderItem
    from app.models.payment import Payment
    from app.models.outlet_rating import OutletRating


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Nullable for COUNTER orders (walk-in, no student account)
    student_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("outlets.id"), nullable=False
    )
    # Nullable for COUNTER orders
    pickup_slot_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pickup_slots.id"), nullable=True
    )

    # PLACED | PREPARING | READY | PICKED | EXPIRED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[float] = mapped_column(Double, nullable=False)
    # ONLINE | CASH
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    # PENDING | PAID | FAILED
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False)
    ready_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # 4-digit OTP stored as string to preserve leading zeros (e.g. "0472")
    pickup_otp: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)

    # PLATFORM (student via app) or COUNTER (manager walk-in)
    # explicit @Column(name = "order_source") in Java — preserved
    order_source: Mapped[str] = mapped_column(String(10), nullable=False, default="PLATFORM")
    # Walk-in customer name for COUNTER orders
    customer_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # Relationships
    student: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[student_id], lazy="joined"
    )
    outlet: Mapped["Outlet"] = relationship("Outlet", back_populates="orders", lazy="joined")
    pickup_slot: Mapped[Optional["PickupSlot"]] = relationship(
        "PickupSlot", back_populates="orders", lazy="select"
    )
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="order")
    rating: Mapped[Optional["OutletRating"]] = relationship(
        "OutletRating", back_populates="order", uselist=False
    )
