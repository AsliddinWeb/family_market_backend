from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.employee import EmploymentType
from app.models.user import UserRole
from app.schemas.branch import BranchShort, DepartmentShort


class EmployeeCreate(BaseModel):
    # User ma'lumotlari (yangi user yaratiladi)
    phone: str
    full_name: str
    password: str
    role: UserRole = UserRole.employee

    # Employee ma'lumotlari
    branch_id: int
    department_id: int
    position: str
    employment_type: EmploymentType = EmploymentType.full
    hire_date: date
    base_salary: Decimal
    telegram_user_id: str | None = None
    photo: str | None = None

    @field_validator("base_salary")
    @classmethod
    def salary_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("base_salary must be positive")
        return v

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("+"):
            raise ValueError("Phone must start with +")
        return v


class EmployeeUpdate(BaseModel):
    branch_id: int | None = None
    department_id: int | None = None
    position: str | None = None
    employment_type: EmploymentType | None = None
    hire_date: date | None = None
    base_salary: Decimal | None = None
    telegram_user_id: str | None = None
    photo: str | None = None
    is_active: bool | None = None
    # User fields
    full_name: str | None = None
    role: UserRole | None = None


class EmployeeOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: str
    role: UserRole
    branch_id: int
    department_id: int
    position: str
    employment_type: EmploymentType
    hire_date: date
    base_salary: Decimal
    telegram_user_id: str | None
    photo: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class EmployeeDetail(EmployeeOut):
    branch: BranchShort
    department: DepartmentShort


class PaginatedEmployees(BaseModel):
    total: int
    page: int
    size: int
    items: list[EmployeeOut]