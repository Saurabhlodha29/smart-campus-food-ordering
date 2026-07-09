"""SQLAlchemy model for the `campuses` table. Source: Campus.java"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.outlet import Outlet
    from app.models.admin_application import AdminApplication
    from app.models.outlet_application import OutletApplication


class Campus(Base):
    __tablename__ = "campuses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    # explicit @Column(name = "email_domain") in Java — preserved
    email_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="campus")
    outlets: Mapped[list["Outlet"]] = relationship("Outlet", back_populates="campus")
