"""Admin endpoints (§70, §71): user management and server TTS settings."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin
from app.core.config import settings
from app.core.errors import APIError
from app.core.runtime import TTS_PROVIDER_KEY, effective_tts_provider, set_setting
from app.core.security import hash_password
from app.db.base import get_session
from app.models.user import User, UserCredential
from app.tts.registry import _ALIASES

router = APIRouter(prefix="/admin", tags=["admin"])


# --- users (§70) ---

class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    created_at: datetime


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "user"


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> list[User]:
    rows = (await session.execute(select(User).order_by(User.created_at))).scalars().all()
    return list(rows)


@router.post("/users", response_model=AdminUserOut, status_code=201)
async def create_user(
    body: AdminUserCreate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    if body.role not in ("user", "admin"):
        raise APIError("invalid_request", "role must be user or admin.", 400)
    existing = (
        await session.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise APIError("conflict", "A user with that email already exists.", 409)
    user = User(email=body.email, role=body.role)
    session.add(user)
    await session.flush()
    session.add(UserCredential(user_id=user.id, password_hash=hash_password(body.password)))
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    if user_id == admin.id:
        raise APIError("invalid_request", "You cannot delete your own account.", 400)
    user = await session.get(User, user_id)
    if user is None:
        raise APIError("not_found", "User not found.", 404)
    await session.delete(user)
    await session.commit()


# --- server TTS settings (§29) ---

class TtsSettingsOut(BaseModel):
    provider: str  # effective (override or env default)
    default_from_env: str
    fallback_provider: str
    available: list[str]


class TtsSettingsUpdate(BaseModel):
    provider: str


@router.get("/settings/tts", response_model=TtsSettingsOut)
async def get_tts_settings(
    _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> TtsSettingsOut:
    return TtsSettingsOut(
        provider=await effective_tts_provider(session, settings),
        default_from_env=settings.tts_provider,
        fallback_provider=settings.tts_fallback_provider,
        available=sorted(set(_ALIASES.values())),
    )


@router.patch("/settings/tts", response_model=TtsSettingsOut)
async def update_tts_settings(
    body: TtsSettingsUpdate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> TtsSettingsOut:
    if body.provider not in _ALIASES:
        raise APIError("invalid_request", f"Unknown provider: {body.provider}", 400)
    await set_setting(session, TTS_PROVIDER_KEY, _ALIASES[body.provider])
    return TtsSettingsOut(
        provider=await effective_tts_provider(session, settings),
        default_from_env=settings.tts_provider,
        fallback_provider=settings.tts_fallback_provider,
        available=sorted(set(_ALIASES.values())),
    )
