"""SQLAlchemy model for the `payments` table. Source: Payment.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.order import Order


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Null for penalty payments
    order_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=True
    )
    # Penalty payment → holds the student's user id; null for order payments
    # explicit @Column(name = "penalty_user_id") in Java — preserved
    penalty_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # rzp_order_XXXX
    razorpay_order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # pay_XXXX — null until verified
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    amount: Mapped[float] = mapped_column(Double, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    # ORDER_PAYMENT | PENALTY_PAYMENT
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # CREATED | SUCCESS | FAILED | REFUNDED
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="payments")
