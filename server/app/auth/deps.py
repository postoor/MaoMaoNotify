"""FastAPI auth dependencies for users and agents."""

from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.scopes import has_scopes
from app.core.errors import APIError
from app.core.security import decode_access_token, hash_token
from app.db.base import get_session
from app.models.agent import Agent, AgentToken
from app.models.device import Device, DeviceCredential
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def _token(creds: HTTPAuthorizationCredentials | None) -> str:
    if creds is None or not creds.credentials:
        raise APIError("unauthorized", "Missing bearer token.", 401)
    return creds.credentials


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = _token(creds)
    try:
        claims = decode_access_token(token)
    except jwt.PyJWTError:
        raise APIError("unauthorized", "Invalid or expired token.", 401)
    user = await session.get(User, claims.get("sub", ""))
    if user is None:
        raise APIError("unauthorized", "Invalid or expired token.", 401)
    return user


@dataclass
class AuthedAgent:
    agent: Agent
    scopes: list[str]


async def get_current_agent(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> AuthedAgent:
    token = _token(creds)
    row = (
        await session.execute(
            select(AgentToken).where(AgentToken.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if row is None or row.revoked:
        raise APIError("unauthorized", "Invalid agent token.", 401)
    agent = await session.get(Agent, row.agent_id)
    if agent is None:
        raise APIError("unauthorized", "Invalid agent token.", 401)
    return AuthedAgent(agent=agent, scopes=list(row.scopes or []))


def require_scopes(*required: str):
    """Dependency factory: 403 unless the agent holds all required scopes."""

    async def _dep(authed: AuthedAgent = Depends(get_current_agent)) -> AuthedAgent:
        if not has_scopes(authed.scopes, set(required)):
            raise APIError("insufficient_scope", "Agent lacks required scope.", 403)
        return authed

    return _dep


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise APIError("forbidden", "Admin role required.", 403)
    return user


async def authenticate_device(session: AsyncSession, token: str) -> Device:
    """Resolve a device from its opaque device token (issued at pairing)."""
    cred = (
        await session.execute(
            select(DeviceCredential).where(DeviceCredential.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if cred is None:
        raise APIError("unauthorized", "Invalid device token.", 401)
    device = await session.get(Device, cred.device_id)
    if device is None:
        raise APIError("unauthorized", "Invalid device token.", 401)
    return device


async def get_current_device(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Device:
    return await authenticate_device(session, _token(creds))
