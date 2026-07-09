"""SQLAlchemy model for the `users` table. Source: User.java"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Double, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.campus import Campus
    from app.models.outlet import Outlet
    from app.models.notification import Notification
    from app.models.outlet_rating import OutletRating


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # SpringPhysicalNamingStrategy: fullName → full_name
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    # No length on @Column → Hibernate default VARCHAR(255)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id"), nullable=False)
    campus_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("campuses.id"), nullable=True
    )

    # primitive boolean → NOT NULL in DB; Java default (true) is application-level only
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    no_show_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Java double (primitive) → DOUBLE PRECISION NOT NULL; spec §10 says keep as float, no Decimal
    pending_penalty_amount: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)
    account_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    phone: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="joined")
    campus: Mapped[Optional["Campus"]] = relationship(
        "Campus", back_populates="users", lazy="select"
    )
    managed_outlets: Mapped[list["Outlet"]] = relationship(
        "Outlet", back_populates="manager", foreign_keys="Outlet.manager_id"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    ratings: Mapped[list["OutletRating"]] = relationship(
        "OutletRating", back_populates="student", foreign_keys="OutletRating.student_id"
    )
