import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class EmploymentType(str, enum.Enum):
    full = "full"
    part = "part"
    contract = "contract"


class Employee(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    position: Mapped[str] = mapped_column(String(100))
    employment_type: Mapped[EmploymentType] = mapped_column(
        default=EmploymentType.full
    )
    hire_date: Mapped[date] = mapped_column(Date)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    telegram_user_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )
    photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    user: Mapped["User"] = relationship(back_populates="employee")
    branch: Mapped["Branch"] = relationship(back_populates="employees")
    department: Mapped["Department"] = relationship(back_populates="employees")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="employee")
    leaves: Mapped[list["Leave"]] = relationship(back_populates="employee")
    salary_records: Mapped[list["SalaryRecord"]] = relationship(back_populates="employee")
    bonuses: Mapped[list["Bonus"]] = relationship(back_populates="employee")
    deductions: Mapped[list["Deduction"]] = relationship(back_populates="employee")
    kpis: Mapped[list["KPI"]] = relationship(back_populates="employee")