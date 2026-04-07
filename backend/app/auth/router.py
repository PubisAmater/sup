import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.telegram import TelegramAuthData, verify_telegram_auth
from app.database import get_async_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram/callback")
async def telegram_callback(
    data: TelegramAuthData,
    session: AsyncSession = Depends(get_async_session),
):
    auth_data = data.model_dump()
    if not verify_telegram_auth(auth_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication",
        )

    result = await session.execute(
        select(User).where(User.telegram_id == data.id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            telegram_id=data.id,
            first_name=data.first_name,
            last_name=data.last_name,
            username=data.username,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "role": user.role,
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(User).where(User.id == uuid.UUID(current_user["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
