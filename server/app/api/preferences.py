"""User-level preferences (§19 manual presence, §20 quiet hours)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.base import get_session
from app.models.user import User, UserPreferences

router = APIRouter(prefix="/preferences", tags=["preferences"])

_VALID_PRESENCE = {"auto", "available", "busy", "away", "do_not_disturb"}


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    manual_presence: str
    quiet_hours: dict
    data: dict


class PreferencesUpdate(BaseModel):
    manual_presence: str | None = None
    quiet_hours: dict | None = None
    data: dict | None = None


async def _get_or_create(session: AsyncSession, user_id: str) -> UserPreferences:
    prefs = await session.get(UserPreferences, user_id)
    if prefs is None:
        prefs = UserPreferences(user_id=user_id)
        session.add(prefs)
        try:
            await session.commit()
        except IntegrityError:
            # A concurrent request created it first — reuse that row.
            await session.rollback()
            prefs = await session.get(UserPreferences, user_id)
        else:
            await session.refresh(prefs)
    return prefs


@router.get("", response_model=PreferencesOut)
async def get_preferences(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> UserPreferences:
    return await _get_or_create(session, user.id)


@router.patch("", response_model=PreferencesOut)
async def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserPreferences:
    from app.core.errors import APIError

    prefs = await _get_or_create(session, user.id)
    if body.manual_presence is not None:
        if body.manual_presence not in _VALID_PRESENCE:
            raise APIError("invalid_request", "Invalid manual_presence value.", 400)
        prefs.manual_presence = body.manual_presence
    if body.quiet_hours is not None:
        prefs.quiet_hours = body.quiet_hours
    if body.data is not None:
        prefs.data = body.data
    await session.commit()
    await session.refresh(prefs)
    return prefs
