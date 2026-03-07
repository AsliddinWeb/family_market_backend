from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginSchema, RefreshSchema, ChangePasswordSchema, TokenResponse
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginSchema,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.login(db, data)


@router.post("/refresh")
async def refresh(data: RefreshSchema):
    return await auth_service.refresh_token(data.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # employee relationship ni selectinload bilan yuklaymiz
    result = await db.execute(
        select(User)
        .options(selectinload(User.employee))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()
    return user


@router.patch("/change-password")
async def change_password(
    data: ChangePasswordSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await auth_service.change_password(
        db, current_user, data.old_password, data.new_password
    )