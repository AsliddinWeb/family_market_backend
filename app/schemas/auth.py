from pydantic import BaseModel
from app.schemas.user import UserOut


class LoginSchema(BaseModel):
    phone: str
    password: str


class RefreshSchema(BaseModel):
    refresh_token: str


class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut