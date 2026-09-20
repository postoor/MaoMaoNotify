"""Agent registry (§8). User-authenticated management of the user's own agents."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.scopes import ALL_SCOPES, DEFAULT_SCOPES
from app.core.errors import APIError
from app.core.security import generate_opaque_token, hash_token
from app.db.base import get_session
from app.models.agent import Agent, AgentToken, AgentWebhook
from app.models.user import User

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[str] | None = None


class AgentCreateOut(BaseModel):
    id: str
    name: str
    scopes: list[str]
    token: str  # shown once


async def _owned_agent(session: AsyncSession, user: User, agent_id: str) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise APIError("not_found", "Agent not found.", 404)
    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[Agent]:
    rows = (
        await session.execute(select(Agent).where(Agent.user_id == user.id))
    ).scalars().all()
    return list(rows)


@router.post("", response_model=AgentCreateOut, status_code=201)
async def create_agent(
    body: AgentCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentCreateOut:
    if body.scopes is None:
        scopes = sorted(DEFAULT_SCOPES)
    else:
        unknown = set(body.scopes) - ALL_SCOPES
        if unknown:
            raise APIError("invalid_scope", f"Unknown scopes: {sorted(unknown)}", 400)
        scopes = sorted(set(body.scopes))

    agent = Agent(user_id=user.id, name=body.name)
    session.add(agent)
    await session.flush()
    raw = generate_opaque_token()
    session.add(AgentToken(agent_id=agent.id, token_hash=hash_token(raw), scopes=scopes))
    await session.commit()
    return AgentCreateOut(id=agent.id, name=agent.name, scopes=scopes, token=raw)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    agent = await _owned_agent(session, user, agent_id)
    await session.delete(agent)
    await session.commit()


# --- webhooks (§66) ---

class WebhookCreate(BaseModel):
    url: str = Field(min_length=1)
    events: list[str] = Field(default_factory=list)


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    events: list[str]


class WebhookCreateOut(WebhookOut):
    secret: str  # shown once


@router.get("/{agent_id}/webhooks", response_model=list[WebhookOut])
async def list_webhooks(
    agent_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AgentWebhook]:
    agent = await _owned_agent(session, user, agent_id)
    rows = (
        await session.execute(select(AgentWebhook).where(AgentWebhook.agent_id == agent.id))
    ).scalars().all()
    return list(rows)


@router.post("/{agent_id}/webhooks", response_model=WebhookCreateOut, status_code=201)
async def create_webhook(
    agent_id: str,
    body: WebhookCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WebhookCreateOut:
    agent = await _owned_agent(session, user, agent_id)
    secret = generate_opaque_token()
    webhook = AgentWebhook(agent_id=agent.id, url=body.url, secret=secret, events=body.events)
    session.add(webhook)
    await session.commit()
    return WebhookCreateOut(id=webhook.id, url=webhook.url, events=webhook.events, secret=secret)
