import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.database import async_session_factory, set_tenant_context
from app.models.user import User
from app.utils.permissions import RoleEnum, has_permission

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    payload = decode_access_token(credentials.credentials)
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )
    return payload


async def get_db(
    current_user: dict = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        tenant_id = current_user.get("tenant_id")
        if tenant_id:
            await set_tenant_context(session, uuid.UUID(tenant_id))
        yield session


async def get_db_no_auth() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def require_role(*roles: RoleEnum):
    async def _check(current_user: dict = Depends(get_current_user)):
        user_role = RoleEnum(current_user.get("role", "line"))
        for role in roles:
            if has_permission(user_role, role):
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return _check
