"""Device registry and pairing (§9–11)."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_device, get_current_user
from app.core.config import settings
from app.core.errors import APIError
from app.core.security import generate_opaque_token, hash_token
from app.db.base import get_session
from app.models.device import Device, DeviceCredential, DevicePreferences, PairingToken
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["devices"])


# --- schemas ---

class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    detected_name: str | None
    display_name: str | None
    platform: str
    architecture: str | None
    capabilities: list[str]
    last_seen_at: datetime | None
    created_at: datetime


class PairingCreateOut(BaseModel):
    pairing_id: str
    token: str  # for QR
    code: str  # 8-digit
    expires_at: datetime


class DeviceUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)


class RedeemRequest(BaseModel):
    token: str | None = None  # from QR
    code: str | None = None  # 8-digit typed
    detected_name: str | None = None
    platform: str
    architecture: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    public_key: str | None = None


class RedeemOut(BaseModel):
    device_id: str
    device_token: str


# --- helpers ---

def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def _owned_device(session: AsyncSession, user: User, device_id: str) -> Device:
    device = await session.get(Device, device_id)
    if device is None or device.user_id != user.id:
        raise APIError("not_found", "Device not found.", 404)
    return device


# --- endpoints ---

@router.get("", response_model=list[DeviceOut])
async def list_devices(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[Device]:
    rows = (
        await session.execute(select(Device).where(Device.user_id == user.id))
    ).scalars().all()
    return list(rows)


@router.post("/pairing", response_model=PairingCreateOut)
async def create_pairing(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> PairingCreateOut:
    raw = generate_opaque_token()
    code = f"{secrets.randbelow(10**8):08d}"
    expires = datetime.now(UTC) + timedelta(minutes=settings.pairing_token_ttl_minutes)
    pairing = PairingToken(
        user_id=user.id, token_hash=hash_token(raw), code=code, expires_at=expires
    )
    session.add(pairing)
    await session.commit()
    return PairingCreateOut(
        pairing_id=pairing.id, token=raw, code=code, expires_at=expires
    )


class PushEndpointIn(BaseModel):
    endpoint: str | None = None  # UnifiedPush endpoint; null clears it


@router.post("/push-endpoint", status_code=200)
async def set_push_endpoint(
    body: PushEndpointIn,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> dict:
    device.push_endpoint = body.endpoint
    await session.commit()
    return {"status": "ok"}


@router.post("/pairing/redeem", response_model=RedeemOut)
async def redeem_pairing(
    body: RedeemRequest, session: AsyncSession = Depends(get_session)
) -> RedeemOut:
    if not body.token and not body.code:
        raise APIError("invalid_request", "Provide a pairing token or code.", 400)
    stmt = select(PairingToken)
    if body.token:
        stmt = stmt.where(PairingToken.token_hash == hash_token(body.token))
    else:
        stmt = stmt.where(PairingToken.code == body.code)
    pairing = (await session.execute(stmt)).scalar_one_or_none()
    if pairing is None or pairing.used or _aware(pairing.expires_at) < datetime.now(UTC):
        raise APIError("invalid_pairing_token", "Pairing token invalid, used, or expired.", 400)

    device_token = generate_opaque_token()
    device = Device(
        user_id=pairing.user_id,
        detected_name=body.detected_name,
        display_name=body.detected_name,
        platform=body.platform,
        architecture=body.architecture,
        capabilities=body.capabilities,
    )
    session.add(device)
    await session.flush()  # assign device.id
    session.add(
        DeviceCredential(
            device_id=device.id,
            public_key=body.public_key,
            token_hash=hash_token(device_token),
        )
    )
    pairing.used = True
    pairing.device_id = device.id
    await session.commit()
    return RedeemOut(device_id=device.id, device_token=device_token)


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: str,
    body: DeviceUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Device:
    device = await _owned_device(session, user, device_id)
    device.display_name = body.display_name
    await session.commit()
    await session.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    device = await _owned_device(session, user, device_id)
    await session.delete(device)
    await session.commit()


# --- device voice policy / preferences (§37) ---

class DevicePrefsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    voice_policy: dict
    data: dict


class DevicePrefsUpdate(BaseModel):
    voice_policy: dict | None = None
    data: dict | None = None


async def _prefs(session: AsyncSession, device_id: str) -> DevicePreferences:
    prefs = await session.get(DevicePreferences, device_id)
    if prefs is None:
        prefs = DevicePreferences(device_id=device_id)
        session.add(prefs)
        await session.commit()
        await session.refresh(prefs)
    return prefs


@router.get("/{device_id}/preferences", response_model=DevicePrefsOut)
async def get_device_prefs(
    device_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DevicePreferences:
    await _owned_device(session, user, device_id)
    return await _prefs(session, device_id)


@router.patch("/{device_id}/preferences", response_model=DevicePrefsOut)
async def update_device_prefs(
    device_id: str,
    body: DevicePrefsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DevicePreferences:
    await _owned_device(session, user, device_id)
    prefs = await _prefs(session, device_id)
    if body.voice_policy is not None:
        prefs.voice_policy = body.voice_policy
    if body.data is not None:
        prefs.data = body.data
    await session.commit()
    await session.refresh(prefs)
    return prefs
