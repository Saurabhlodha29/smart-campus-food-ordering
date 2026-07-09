"""SQLAlchemy model for the `outlet_ratings` table. Source: OutletRating.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.outlet import Outlet
    from app.models.user import User
    from app.models.order import Order


class OutletRating(Base):
    __tablename__ = "outlet_ratings"
    __table_args__ = (
        # @UniqueConstraint(columnNames = {"order_id"}) — one rating per order
        UniqueConstraint("order_id", name="uq_outlet_ratings_order_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("outlets.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    # @OneToOne with unique=true — enforced by the UniqueConstraint above
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=False, unique=True
    )
    # 1–5 stars
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    outlet: Mapped["Outlet"] = relationship(
        "Outlet", back_populates="ratings", foreign_keys=[outlet_id], lazy="joined"
    )
    student: Mapped["User"] = relationship(
        "User", back_populates="ratings", foreign_keys=[student_id], lazy="joined"
    )
    order: Mapped["Order"] = relationship(
        "Order", back_populates="rating", foreign_keys=[order_id]
    )
