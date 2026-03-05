from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.user import User
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.auth import LoginSchema, TokenResponse
from jose import JWTError


async def login(db: AsyncSession, data: LoginSchema) -> TokenResponse:
    # Userni topish
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    if not user.is_active or user.is_deleted:
        raise HTTPException(status_code=401, detail="User is inactive")

    payload = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


async def refresh_token(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_payload = {"sub": payload["sub"], "role": payload["role"]}
    return {
        "access_token": create_access_token(new_payload),
        "token_type": "bearer",
    }


async def change_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
) -> dict:
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    user.hashed_password = hash_password(new_password)
    await db.commit()
    return {"message": "Password changed successfully"}