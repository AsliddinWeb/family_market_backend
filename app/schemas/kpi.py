from pydantic import BaseModel, field_validator


class KPICreate(BaseModel):
    employee_id: int
    period_year: int
    period_month: int
    metric_name: str
    target_value: float
    actual_value: float = 0
    weight: float = 100
    notes: str | None = None

    @field_validator("period_month")
    @classmethod
    def valid_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("period_month must be 1-12")
        return v

    @field_validator("weight")
    @classmethod
    def valid_weight(cls, v: float) -> float:
        if not 0 < v <= 100:
            raise ValueError("weight must be 0-100")
        return v


class KPIUpdate(BaseModel):
    actual_value: float | None = None
    target_value: float | None = None
    weight: float | None = None
    notes: str | None = None


class KPIOut(BaseModel):
    id: int
    employee_id: int
    period_year: int
    period_month: int
    metric_name: str
    target_value: float
    actual_value: float
    weight: float
    score: float  # computed: actual/target * weight
    notes: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_score(cls, obj) -> "KPIOut":
        score = 0.0
        if obj.target_value > 0:
            score = round((obj.actual_value / obj.target_value) * obj.weight, 2)
        return cls(
            id=obj.id,
            employee_id=obj.employee_id,
            period_year=obj.period_year,
            period_month=obj.period_month,
            metric_name=obj.metric_name,
            target_value=obj.target_value,
            actual_value=obj.actual_value,
            weight=obj.weight,
            score=score,
            notes=obj.notes,
        )


class PaginatedKPI(BaseModel):
    total: int
    page: int
    size: int
    items: list[KPIOut]


# ── KPITemplate ──────────────────────────────────────────────

class KPITemplateCreate(BaseModel):
    department_id: int | None = None
    metric_name: str
    description: str | None = None
    target_value: float
    weight: float = 100
    is_active: bool = True


class KPITemplateUpdate(BaseModel):
    metric_name: str | None = None
    description: str | None = None
    target_value: float | None = None
    weight: float | None = None
    is_active: bool | None = None


class KPITemplateOut(BaseModel):
    id: int
    department_id: int | None
    metric_name: str
    description: str | None
    target_value: float
    weight: float
    is_active: bool

    model_config = {"from_attributes": True}


class KPISummary(BaseModel):
    employee_id: int
    period_year: int
    period_month: int
    total_score: float
    max_score: float
    percentage: float
    kpi_count: int