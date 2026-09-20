"""Agent registry, agent tokens (with scopes), and agent webhooks."""

from datetime import datetime
from functools import partial

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base
from app.models.mixins import TimestampMixin, _utcnow


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "agt"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String)

    tokens: Mapped[list["AgentToken"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["AgentWebhook"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "atok"))
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)  # §8
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    agent: Mapped[Agent] = relationship(back_populates="tokens")


class AgentWebhook(Base):
    __tablename__ = "agent_webhooks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "whk"))
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String)
    secret: Mapped[str] = mapped_column(String)  # HMAC signing secret (§66)
    events: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    agent: Mapped[Agent] = relationship(back_populates="webhooks")
