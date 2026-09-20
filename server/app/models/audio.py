"""Audio assets (§35, §67): server-TTS output or agent-uploaded audio."""

from datetime import datetime
from functools import partial

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ids import new_id
from app.db.base import Base
from app.models.mixins import _utcnow


class AudioAsset(Base):
    __tablename__ = "audio_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "audio"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String)  # server_tts | agent_audio
    provider: Mapped[str | None] = mapped_column(String, nullable=True)  # edge_tts, piper, ...
    content_type: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
