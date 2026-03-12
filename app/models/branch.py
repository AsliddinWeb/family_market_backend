from datetime import time
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Time, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class Branch(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    work_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    work_end_time: Mapped[time] = mapped_column(Time, default=time(18, 0))

    # Geofence — filial joylashuvi va ruxsat berilgan radius
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    radius_meters: Mapped[int] = mapped_column(Integer, default=200)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    departments: Mapped[list["Department"]] = relationship(back_populates="branch")
    employees: Mapped[list["Employee"]] = relationship(back_populates="branch")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    head_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    branch: Mapped["Branch"] = relationship(back_populates="departments")
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")