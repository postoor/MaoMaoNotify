"""Multi-user isolation (§6): one user must never see or touch another's data."""


async def _make_device(client, headers) -> str:
    pairing = await client.post("/api/v1/devices/pairing", headers=headers)
    code = pairing.json()["code"]
    redeem = await client.post(
        "/api/v1/devices/pairing/redeem",
        json={"code": code, "platform": "linux", "detected_name": "box"},
    )
    return redeem.json()["device_id"]


async def test_devices_isolated_between_users(client, auth_headers):
    a = await auth_headers("a@example.com")
    b = await auth_headers("b@example.com")

    dev_a = await _make_device(client, a)
    await _make_device(client, b)

    list_a = await client.get("/api/v1/devices", headers=a)
    ids_a = {d["id"] for d in list_a.json()}
    assert dev_a in ids_a

    list_b = await client.get("/api/v1/devices", headers=b)
    ids_b = {d["id"] for d in list_b.json()}
    assert dev_a not in ids_b
    assert len(ids_b) == 1


async def test_cannot_patch_other_users_device(client, auth_headers):
    a = await auth_headers("a@example.com")
    b = await auth_headers("b@example.com")
    dev_a = await _make_device(client, a)

    resp = await client.patch(
        f"/api/v1/devices/{dev_a}", headers=b, json={"display_name": "hijacked"}
    )
    assert resp.status_code == 404


async def test_cannot_delete_other_users_device(client, auth_headers):
    a = await auth_headers("a@example.com")
    b = await auth_headers("b@example.com")
    dev_a = await _make_device(client, a)

    resp = await client.delete(f"/api/v1/devices/{dev_a}", headers=b)
    assert resp.status_code == 404

    # still present for owner
    still = await client.get("/api/v1/devices", headers=a)
    assert dev_a in {d["id"] for d in still.json()}


async def test_agents_isolated_between_users(client, auth_headers):
    a = await auth_headers("a@example.com")
    b = await auth_headers("b@example.com")

    created = await client.post("/api/v1/agents", headers=a, json={"name": "claude-code"})
    agent_a = created.json()["id"]

    list_b = await client.get("/api/v1/agents", headers=b)
    assert agent_a not in {x["id"] for x in list_b.json()}

    resp = await client.delete(f"/api/v1/agents/{agent_a}", headers=b)
    assert resp.status_code == 404
