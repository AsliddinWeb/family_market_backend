import enum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    hr_manager = "hr_manager"
    branch_manager = "branch_manager"
    accountant = "accountant"
    employee = "employee"


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(default=UserRole.employee)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relations
    employee: Mapped["Employee | None"] = relationship(
        back_populates="user", uselist=False
    )