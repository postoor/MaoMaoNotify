"""Admin-editable runtime settings, layered over environment defaults."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.app_setting import AppSetting

TTS_PROVIDER_KEY = "tts_provider"


async def get_setting(session: AsyncSession, key: str) -> object | None:
    row = await session.get(AppSetting, key)
    return row.value.get("value") if row and isinstance(row.value, dict) else None


async def set_setting(session: AsyncSession, key: str, value: object) -> None:
    row = await session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value={"value": value}))
    else:
        row.value = {"value": value}
    await session.commit()


async def effective_tts_provider(session: AsyncSession, settings: Settings) -> str:
    override = await get_setting(session, TTS_PROVIDER_KEY)
    return override if isinstance(override, str) and override else settings.tts_provider
