"""Authentication service: verify credentials, issue and rotate tokens."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import APIError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_token,
    verify_password,
)
from app.models.user import RefreshToken, User, UserCredential


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        raise APIError("invalid_credentials", "Invalid email or password.", 401)
    cred = await session.get(UserCredential, user.id)
    if cred is None or not verify_password(password, cred.password_hash):
        raise APIError("invalid_credentials", "Invalid email or password.", 401)
    return user


async def _issue_refresh(session: AsyncSession, user_id: str) -> str:
    raw = generate_opaque_token()
    expires = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    session.add(RefreshToken(user_id=user_id, token_hash=hash_token(raw), expires_at=expires))
    return raw


async def issue_tokens(session: AsyncSession, user: User) -> dict[str, str]:
    access = create_access_token(user.id, extra={"role": user.role})
    refresh = await _issue_refresh(session, user.id)
    await session.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def rotate_refresh(session: AsyncSession, refresh_token: str) -> dict[str, str]:
    row = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    expires_at = row.expires_at if row else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if row is None or row.revoked or expires_at < now:
        raise APIError("invalid_refresh_token", "Refresh token is invalid or expired.", 401)
    row.revoked = True  # rotate: single-use refresh tokens
    user = await session.get(User, row.user_id)
    if user is None:
        raise APIError("invalid_refresh_token", "Refresh token is invalid or expired.", 401)
    access = create_access_token(user.id, extra={"role": user.role})
    new_refresh = await _issue_refresh(session, user.id)
    await session.commit()
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}
