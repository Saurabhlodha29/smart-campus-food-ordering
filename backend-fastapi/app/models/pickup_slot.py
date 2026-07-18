"""
SQLAlchemy model for the `pickup_slots` table. Source: PickupSlot.java

Critical: @Version-based optimistic locking must be wired here via
`version_id_col` mapper arg. SQLAlchemy auto-increments this on every UPDATE,
matching Hibernate @Version behaviour. The service layer must catch
StaleDataError and retry exactly once (spec §4.4).
"""
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.outlet import Outlet
    from app.models.order import Order


class PickupSlot(Base):
    __tablename__ = "pickup_slots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("outlets.id"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Derived from start_time at creation — used for efficient date-filtered queries
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    max_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    current_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Hibernate @Version → SQLAlchemy version_id_col (BigInteger matches Java Long)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Hibernate's @Version initialises the field to 0L and the JPA provider
    # persists that 0 on INSERT, then bumps to 1 on the first UPDATE. SQLAlchemy's
    # default ``version_id_generator`` returns 1 for ``None`` (new instance),
    # which would make freshly-inserted rows start at version=1 — diverging
    # from the Java wire format. The custom generator below reproduces Hibernate
    # behaviour exactly: INSERT → 0, UPDATE → 1, UPDATE → 2, ...
    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": lambda v: 0 if v is None else v + 1,
    }

    # Relationships
    outlet: Mapped["Outlet"] = relationship(
        "Outlet", back_populates="pickup_slots", lazy="joined"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="pickup_slot")
