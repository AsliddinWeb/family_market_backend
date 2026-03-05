import enum
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class LeaveType(str, enum.Enum):
    annual = "annual"        # yillik ta'til
    sick = "sick"            # kasallik
    unpaid = "unpaid"        # haqsiz ta'til
    maternity = "maternity"  # dekret
    other = "other"


class LeaveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class Leave(Base, TimestampMixin):
    __tablename__ = "leaves"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[LeaveType] = mapped_column(default=LeaveType.annual)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days_count: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LeaveStatus] = mapped_column(default=LeaveStatus.pending)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relations
    employee: Mapped["Employee"] = relationship(back_populates="leaves")
    approved_by: Mapped["User | None"] = relationship(foreign_keys=[approved_by_id])