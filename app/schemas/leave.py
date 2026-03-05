from datetime import date

from pydantic import BaseModel, model_validator

from app.models.leave import LeaveStatus, LeaveType


class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: LeaveType = LeaveType.annual
    start_date: date
    end_date: date
    reason: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "LeaveCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class LeaveStatusUpdate(BaseModel):
    status: LeaveStatus
    rejection_reason: str | None = None


class LeaveOut(BaseModel):
    id: int
    employee_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_count: int
    reason: str | None
    status: LeaveStatus
    approved_by_id: int | None
    rejection_reason: str | None

    model_config = {"from_attributes": True}


class PaginatedLeaves(BaseModel):
    total: int
    page: int
    size: int
    items: list[LeaveOut]