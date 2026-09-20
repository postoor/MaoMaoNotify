async def test_login_success(client, create_user):
    await create_user("a@example.com", "pw-secret-123")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "pw-secret-123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client, create_user):
    await create_user("a@example.com", "pw-secret-123")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"}
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_me_returns_current_user(client, auth_headers):
    headers = await auth_headers("a@example.com")
    resp = await client.get("/api/v1/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "a@example.com"


async def test_refresh_rotates_token(client, create_user):
    await create_user("a@example.com", "pw-secret-123")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "pw-secret-123"}
    )
    old_refresh = login.json()["refresh_token"]

    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != old_refresh

    # old refresh token is single-use: rejected after rotation
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "invalid_refresh_token"


async def test_refresh_invalid_token(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401
