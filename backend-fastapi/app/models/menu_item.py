"""SQLAlchemy model for the `menu_items` table. Source: MenuItem.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Double, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.outlet import Outlet
    from app.models.order_item import OrderItem


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("outlets.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[float] = mapped_column(Double, nullable=False)
    prep_time: Mapped[int] = mapped_column(Integer, nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # primitive boolean isAvailable → is_available (SpringPhysicalNamingStrategy)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    outlet: Mapped["Outlet"] = relationship("Outlet", back_populates="menu_items", lazy="joined")
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="menu_item"
    )
