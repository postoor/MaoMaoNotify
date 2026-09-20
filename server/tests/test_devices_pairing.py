"""Device pairing flow (§9)."""


async def test_pairing_and_redeem(client, auth_headers):
    headers = await auth_headers("a@example.com")

    pairing = await client.post("/api/v1/devices/pairing", headers=headers)
    assert pairing.status_code == 200
    data = pairing.json()
    assert len(data["code"]) == 8 and data["token"]

    redeem = await client.post(
        "/api/v1/devices/pairing/redeem",
        json={
            "token": data["token"],
            "platform": "macos",
            "architecture": "arm64",
            "detected_name": "MacBookPro18,3",
            "capabilities": ["text_notification", "client_tts"],
        },
    )
    assert redeem.status_code == 200
    body = redeem.json()
    assert body["device_id"].startswith("dev_")
    assert body["device_token"]

    listing = await client.get("/api/v1/devices", headers=headers)
    devices = listing.json()
    assert len(devices) == 1
    assert devices[0]["platform"] == "macos"
    assert devices[0]["capabilities"] == ["text_notification", "client_tts"]


async def test_pairing_token_single_use(client, auth_headers):
    headers = await auth_headers("a@example.com")
    pairing = (await client.post("/api/v1/devices/pairing", headers=headers)).json()

    first = await client.post(
        "/api/v1/devices/pairing/redeem",
        json={"token": pairing["token"], "platform": "linux"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/devices/pairing/redeem",
        json={"token": pairing["token"], "platform": "linux"},
    )
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "invalid_pairing_token"


async def test_redeem_requires_token_or_code(client):
    resp = await client.post("/api/v1/devices/pairing/redeem", json={"platform": "linux"})
    assert resp.status_code == 400


async def test_update_display_name(client, auth_headers):
    headers = await auth_headers("a@example.com")
    pairing = (await client.post("/api/v1/devices/pairing", headers=headers)).json()
    dev = (
        await client.post(
            "/api/v1/devices/pairing/redeem",
            json={"code": pairing["code"], "platform": "linux"},
        )
    ).json()["device_id"]

    resp = await client.patch(
        f"/api/v1/devices/{dev}", headers=headers, json={"display_name": "工作 Linux"}
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "工作 Linux"
