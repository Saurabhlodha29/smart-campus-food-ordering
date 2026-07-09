"""SQLAlchemy model for the `order_items` table. Source: OrderItem.java"""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Double, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.menu_item import MenuItem


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), nullable=False
    )
    menu_item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("menu_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_order: Mapped[float] = mapped_column(Double, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship(
        "MenuItem", back_populates="order_items", lazy="joined"
    )
