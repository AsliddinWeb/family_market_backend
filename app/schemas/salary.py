from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.salary import BonusType, DeductionType, SalaryStatus


class SalaryRecordOut(BaseModel):
    id: int
    employee_id: int
    period_year: int
    period_month: int
    base_salary: Decimal
    total_bonus: Decimal
    total_deduction: Decimal
    late_deduction: Decimal
    leave_deduction: Decimal
    net_salary: Decimal  # computed
    status: SalaryStatus
    paid_at: datetime | None
    notes: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_net(cls, obj) -> "SalaryRecordOut":
        net = obj.base_salary + obj.total_bonus - obj.total_deduction
        return cls(
            id=obj.id,
            employee_id=obj.employee_id,
            period_year=obj.period_year,
            period_month=obj.period_month,
            base_salary=obj.base_salary,
            total_bonus=obj.total_bonus,
            total_deduction=obj.total_deduction,
            late_deduction=obj.late_deduction,
            leave_deduction=obj.leave_deduction,
            net_salary=net,
            status=obj.status,
            paid_at=obj.paid_at,
            notes=obj.notes,
        )


class SalaryRecordCreate(BaseModel):
    employee_id: int
    period_year: int
    period_month: int
    notes: str | None = None

    @field_validator("period_month")
    @classmethod
    def valid_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("period_month must be 1-12")
        return v


class SalaryStatusUpdate(BaseModel):
    status: SalaryStatus
    notes: str | None = None


class PaginatedSalaryRecords(BaseModel):
    total: int
    page: int
    size: int
    items: list[SalaryRecordOut]


# ── Bonus ────────────────────────────────────────────────────

class BonusCreate(BaseModel):
    employee_id: int
    amount: Decimal
    reason: str
    bonus_type: BonusType = BonusType.extra
    period_year: int
    period_month: int

    @field_validator("amount")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class BonusOut(BaseModel):
    id: int
    employee_id: int
    amount: Decimal
    reason: str
    bonus_type: BonusType
    period_year: int
    period_month: int
    approved_by_id: int | None

    model_config = {"from_attributes": True}


class PaginatedBonuses(BaseModel):
    total: int
    page: int
    size: int
    items: list[BonusOut]


# ── Deduction ────────────────────────────────────────────────

class DeductionCreate(BaseModel):
    employee_id: int
    amount: Decimal
    reason: str
    deduction_type: DeductionType = DeductionType.other
    period_year: int
    period_month: int

    @field_validator("amount")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class DeductionOut(BaseModel):
    id: int
    employee_id: int
    amount: Decimal
    reason: str
    deduction_type: DeductionType
    period_year: int
    period_month: int
    auto_generated: bool

    model_config = {"from_attributes": True}


class PaginatedDeductions(BaseModel):
    total: int
    page: int
    size: int
    items: list[DeductionOut]