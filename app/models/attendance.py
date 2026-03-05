import enum
from datetime import date, time

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    half_day = "half_day"
    holiday = "holiday"


class AttendanceSource(str, enum.Enum):
    telegram = "telegram"
    manual = "manual"


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    check_in_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_in_photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    check_out_photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    check_in_location: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    check_out_location: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        default=AttendanceStatus.present
    )
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[AttendanceSource] = mapped_column(
        default=AttendanceSource.manual
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    employee: Mapped["Employee"] = relationship(back_populates="attendances")

    __table_args__ = (UniqueConstraint("employee_id", "date"),)