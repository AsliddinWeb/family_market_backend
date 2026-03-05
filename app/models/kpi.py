from sqlalchemy import Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class KPI(Base, TimestampMixin):
    __tablename__ = "kpi"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(String(100))
    target_value: Mapped[float] = mapped_column(Float)
    actual_value: Mapped[float] = mapped_column(Float, default=0)
    weight: Mapped[float] = mapped_column(Float, default=100)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relations
    employee: Mapped["Employee"] = relationship(back_populates="kpis")


class KPITemplate(Base, TimestampMixin):
    __tablename__ = "kpi_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    metric_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)