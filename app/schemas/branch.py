from datetime import time
from pydantic import BaseModel, field_validator


class BranchCreate(BaseModel):
    name: str
    address: str
    phone: str | None = None
    manager_id: int | None = None
    work_start_time: time = time(9, 0)
    is_active: bool = True


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    manager_id: int | None = None
    work_start_time: time | None = None
    is_active: bool | None = None


class BranchOut(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None
    manager_id: int | None
    work_start_time: time
    is_active: bool

    model_config = {"from_attributes": True}


class BranchShort(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Department ──────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    branch_id: int
    head_id: int | None = None
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = None
    branch_id: int | None = None
    head_id: int | None = None
    is_active: bool | None = None


class DepartmentOut(BaseModel):
    id: int
    name: str
    branch_id: int
    head_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}


class DepartmentShort(BaseModel):
    id: int
    name: str
    branch_id: int
    is_active: bool

    model_config = {"from_attributes": True}


class PaginatedBranches(BaseModel):
    total: int
    page: int
    size: int
    items: list[BranchOut]


class PaginatedDepartments(BaseModel):
    total: int
    page: int
    size: int
    items: list[DepartmentOut]