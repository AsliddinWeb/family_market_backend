from datetime import date, time
from decimal import Decimal
from typing import List

from pydantic import BaseModel, field_validator

from app.models.employee import EmploymentType
from app.models.user import UserRole
from app.schemas.branch import BranchShort, DepartmentShort

VALID_OFF_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


class EmployeeCreate(BaseModel):
    phone: str
    full_name: str
    password: str
    role: UserRole = UserRole.employee

    branch_id: int
    department_id: int
    position: str
    employment_type: EmploymentType = EmploymentType.full
    hire_date: date
    base_salary: Decimal

    hourly_rate: Decimal | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None
    work_hours_per_day: int = 8
    off_days: List[str] = ["saturday", "sunday"]
    custom_off_days: List[str] = []
    custom_work_days: List[str] = []

    telegram_user_id: str | None = None
    photo: str | None = None
    face_photo: str | None = None

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

    @field_validator("off_days")
    @classmethod
    def validate_off_days(cls, v: list) -> list:
        for day in v:
            if day not in VALID_OFF_DAYS:
                raise ValueError(f"Invalid day: {day}. Must be one of {VALID_OFF_DAYS}")
        return v

    @field_validator("work_hours_per_day")
    @classmethod
    def validate_work_hours(cls, v: int) -> int:
        if not (1 <= v <= 24):
            raise ValueError("work_hours_per_day must be between 1 and 24")
        return v


class EmployeeUpdate(BaseModel):
    branch_id: int | None = None
    department_id: int | None = None
    position: str | None = None
    employment_type: EmploymentType | None = None
    hire_date: date | None = None
    base_salary: Decimal | None = None
    hourly_rate: Decimal | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None
    work_hours_per_day: int | None = None
    off_days: List[str] | None = None
    custom_off_days: List[str] | None = None   # aniq sana dam olish kunlari
    custom_work_days: List[str] | None = None  # aniq sana ish kunlari (override)
    telegram_user_id: str | None = None
    photo: str | None = None
    face_photo: str | None = None
    is_active: bool | None = None
    full_name: str | None = None
    role: UserRole | None = None

    @field_validator("off_days")
    @classmethod
    def validate_off_days(cls, v):
        if v is None:
            return v
        for day in v:
            if day not in VALID_OFF_DAYS:
                raise ValueError(f"Invalid day: {day}")
        return v


class EmployeeOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: str
    role: UserRole
    branch_id: int | None = None
    department_id: int | None = None
    position: str | None = None
    employment_type: EmploymentType
    hire_date: date | None = None
    base_salary: Decimal
    hourly_rate: Decimal | None = None
    work_start_time: time | None = None
    work_end_time: time | None = None
    work_hours_per_day: int = 8
    off_days: List[str] = ["saturday", "sunday"]
    custom_off_days: List[str] = []
    custom_work_days: List[str] = []
    telegram_user_id: str | None = None
    photo: str | None = None
    face_photo: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class EmployeeDetail(EmployeeOut):
    branch: BranchShort | None = None
    department: DepartmentShort | None = None


class PaginatedEmployees(BaseModel):
    total: int
    page: int
    size: int
    items: list[EmployeeDetail]