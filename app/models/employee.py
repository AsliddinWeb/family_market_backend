import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class EmploymentType(str, enum.Enum):
    full = "full"
    part = "part"
    contract = "contract"


# Hafta kunlari — off_days JSON arrayida ishlatiladi
# 0=Dushanba, 1=Seshanba, ..., 5=Shanba, 6=Yakshanba
WEEKDAY_NAMES = {
    0: "monday", 1: "tuesday", 2: "wednesday",
    3: "thursday", 4: "friday", 5: "saturday", 6: "sunday",
}
WEEKDAY_NUMBERS = {v: k for k, v in WEEKDAY_NAMES.items()}


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

    # Ish vaqti sozlamalari
    hourly_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True,
        comment="Soatlik stavka. Agar None bo'lsa base_salary/work_hours_per_day/22 dan hisoblanadi"
    )
    work_hours_per_day: Mapped[int] = mapped_column(
        Integer, default=8,
        comment="Kunlik ish soati (default 8)"
    )
    off_days: Mapped[list] = mapped_column(
        JSON, default=["saturday", "sunday"],
        comment="Dam olish kunlari: ['saturday', 'sunday']"
    )

    # Rasm — ikki alohida field
    photo: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Profil rasmi yo'li"
    )
    face_photo: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Yuz tanish uchun referans rasm yo'li"
    )

    telegram_user_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )
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

    def get_effective_hourly_rate(self) -> Decimal:
        """
        Soatlik stavkani hisoblash:
        1. hourly_rate belgilangan bo'lsa → uni ishlatadi
        2. Aks holda → base_salary / (work_hours_per_day * 22)
        """
        if self.hourly_rate:
            return self.hourly_rate
        working_hours_per_month = Decimal(self.work_hours_per_day * 22)
        return self.base_salary / working_hours_per_month

    def is_off_day(self, d: date) -> bool:
        """Berilgan sana dam olish kuni ekanligini tekshiradi"""
        day_name = WEEKDAY_NAMES[d.weekday()]
        return day_name in (self.off_days or [])