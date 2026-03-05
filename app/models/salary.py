import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class SalaryStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    paid = "paid"


class BonusType(str, enum.Enum):
    performance = "performance"
    holiday = "holiday"
    extra = "extra"


class DeductionType(str, enum.Enum):
    late = "late"
    absence = "absence"
    damage = "damage"
    other = "other"


class SalaryRecord(Base, TimestampMixin):
    __tablename__ = "salary_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    total_bonus: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_deduction: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    late_deduction: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    leave_deduction: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    status: Mapped[SalaryStatus] = mapped_column(default=SalaryStatus.draft)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    employee: Mapped["Employee"] = relationship(back_populates="salary_records")

    __table_args__ = (UniqueConstraint("employee_id", "period_year", "period_month"),)


class Bonus(Base, TimestampMixin):
    __tablename__ = "bonuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    reason: Mapped[str] = mapped_column(String(255))
    bonus_type: Mapped[BonusType] = mapped_column(default=BonusType.extra)
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relations
    employee: Mapped["Employee"] = relationship(back_populates="bonuses")
    approved_by: Mapped["User | None"] = relationship(foreign_keys=[approved_by_id])


class Deduction(Base, TimestampMixin):
    __tablename__ = "deductions"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    reason: Mapped[str] = mapped_column(String(255))
    deduction_type: Mapped[DeductionType] = mapped_column(default=DeductionType.other)
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relations
    employee: Mapped["Employee"] = relationship(back_populates="deductions")