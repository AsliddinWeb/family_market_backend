from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    phone: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserShort(BaseModel):
    id: int
    full_name: str
    phone: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)