"""Test fixtures: in-memory SQLite, fakeredis, dependency-overridden app."""

from collections.abc import AsyncIterator, Callable

import fakeredis.aioredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models
from app.core.security import generate_opaque_token, hash_password, hash_token
from app.db.base import Base, get_session
from app.db.redis import get_redis
from app.main import app
from app.models.agent import Agent, AgentToken
from app.models.device import Device, DeviceCredential
from app.models.user import User, UserCredential
from app.storage.deps import get_storage
from app.storage.memory import InMemoryStorage
from app.websocket.manager import manager


@pytest_asyncio.fixture(autouse=True)
def _no_fallback_timer():
    # Tests drive run_fallback / schedule_fallback explicitly; keep the
    # create-notification path from spawning real-DB background timers.
    from app.core.config import settings

    original = settings.fallback_timer_enabled
    settings.fallback_timer_enabled = False
    yield
    settings.fallback_timer_enabled = original


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest_asyncio.fixture
async def client(sessionmaker, redis, storage) -> AsyncIterator[AsyncClient]:
    async def _get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    async def _get_redis():
        return redis

    manager._conns.clear()
    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_redis] = _get_redis
    app.dependency_overrides[get_storage] = lambda: storage
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    manager._conns.clear()


@pytest_asyncio.fixture
async def create_user(sessionmaker) -> Callable:
    async def _create(email: str, password: str = "pw-secret-123", role: str = "user") -> str:
        async with sessionmaker() as session:
            user = User(email=email, role=role)
            session.add(user)
            await session.flush()
            session.add(
                UserCredential(user_id=user.id, password_hash=hash_password(password))
            )
            await session.commit()
            return user.id

    return _create


@pytest_asyncio.fixture
async def auth_headers(client, create_user) -> Callable:
    async def _login(email: str, password: str = "pw-secret-123") -> dict[str, str]:
        await create_user(email, password)
        resp = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


@pytest_asyncio.fixture
async def make_device(sessionmaker) -> Callable:
    """Create a device for a user and return (device_id, device_token)."""

    async def _make(user_id: str, platform: str = "macos") -> tuple[str, str]:
        async with sessionmaker() as session:
            device = Device(user_id=user_id, platform=platform, display_name=platform)
            session.add(device)
            await session.flush()
            token = generate_opaque_token()
            session.add(
                DeviceCredential(device_id=device.id, token_hash=hash_token(token))
            )
            await session.commit()
            return device.id, token

    return _make


@pytest_asyncio.fixture
async def make_agent(sessionmaker) -> Callable:
    """Create an agent + token and return (agent_id, raw_token)."""

    async def _make(user_id: str, scopes: list[str]) -> tuple[str, str]:
        async with sessionmaker() as session:
            agent = Agent(user_id=user_id, name="test-agent")
            session.add(agent)
            await session.flush()
            token = generate_opaque_token()
            session.add(
                AgentToken(agent_id=agent.id, token_hash=hash_token(token), scopes=scopes)
            )
            await session.commit()
            return agent.id, token

    return _make
