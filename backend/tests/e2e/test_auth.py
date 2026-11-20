import asyncio
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.core.infrastructure.database.database import get_async_session_maker
from src.core.infrastructure.database.models.auth import AuthSessionModel

ORIGIN = {"Origin": "http://localhost:5173"}
LOGIN = {"username": "test-analyst", "password": "test-password-long"}


async def test_business_api_requires_bearer(client: AsyncClient) -> None:
    client.headers.pop("Authorization")
    assert (await client.get("/api/v1/officials")).status_code == 401
    assert (await client.get("/health")).status_code == 200


async def test_login_refresh_logout_revokes_access(client: AsyncClient) -> None:
    client.headers.pop("Authorization")
    response = await client.post("/api/v1/auth/login", json=LOGIN, headers=ORIGIN)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    first_cookie = client.cookies.get("kodprozr_refresh")
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()[
        "username"
    ] == "test-analyst"
    refreshed = await client.post("/api/v1/auth/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200
    assert client.cookies.get("kodprozr_refresh") != first_cookie
    # Old opaque refresh cannot be exchanged a second time.
    replay = await client.post(
        "/api/v1/auth/refresh", headers={**ORIGIN, "Cookie": f"kodprozr_refresh={first_cookie}"}
    )
    assert replay.status_code == 401
    assert (await client.post("/api/v1/auth/logout", headers=ORIGIN)).status_code == 204
    assert (await client.get("/api/v1/officials", headers=headers)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", headers=ORIGIN)).status_code == 401


async def test_wrong_password_and_origin(client: AsyncClient) -> None:
    wrong = await client.post(
        "/api/v1/auth/login", json={**LOGIN, "password": "wrong"}, headers=ORIGIN
    )
    absent = await client.post(
        "/api/v1/auth/login", json={**LOGIN, "username": "absent"}, headers=ORIGIN
    )
    assert wrong.status_code == absent.status_code == 401
    assert wrong.json()["detail"] == absent.json()["detail"]
    assert (
        await client.post(
            "/api/v1/auth/login", json=LOGIN, headers={"Origin": "https://evil.example"}
        )
    ).status_code == 403
    assert (await client.post("/api/v1/auth/refresh")).status_code == 403
    assert (await client.post("/api/v1/auth/logout")).status_code == 403


async def test_tampered_token(client: AsyncClient) -> None:
    token = client.headers["Authorization"].split()[1]
    assert (
        await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + token[:-8] + "tampered"}
        )
    ).status_code == 401


async def test_logout_revokes_even_when_refresh_rotates_concurrently(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = await client.post("/api/v1/auth/login", json=LOGIN, headers=ORIGIN)
    assert response.status_code == 200
    old_cookie = client.cookies.get("kodprozr_refresh")
    locked, proceed, logout_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original_commit = AsyncSession.commit

    async def delayed_commit(db: AsyncSession) -> None:
        if any(isinstance(row, AuthSessionModel) for row in db.dirty):
            locked.set()
            await proceed.wait()
        await original_commit(db)

    monkeypatch.setattr(AsyncSession, "commit", delayed_commit)
    refresh_task = asyncio.create_task(client.post("/api/v1/auth/refresh", headers=ORIGIN))
    await asyncio.wait_for(locked.wait(), timeout=5)

    async def leave() -> Any:
        logout_started.set()
        # No access bearer: logout must authenticate the stable proof in the old cookie.
        return await client.post(
            "/api/v1/auth/logout",
            headers={**ORIGIN, "Authorization": "", "Cookie": f"kodprozr_refresh={old_cookie}"},
        )

    logout_task = asyncio.create_task(leave())
    await logout_started.wait()
    await asyncio.sleep(0)
    proceed.set()
    refreshed, logged_out = await asyncio.gather(refresh_task, logout_task)
    assert refreshed.status_code == 200
    assert logged_out.status_code == 204
    assert (
        await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer " + refreshed.json()["access_token"]},
        )
    ).status_code == 401


async def test_revoked_session_cannot_refresh(client: AsyncClient, engine: AsyncEngine) -> None:
    response = await client.post("/api/v1/auth/login", json=LOGIN, headers=ORIGIN)
    session_id = UUID(response.json()["session_id"])
    async with get_async_session_maker(engine)() as db:
        row = (
            await db.execute(select(AuthSessionModel).where(AuthSessionModel.id == session_id))
        ).scalar_one()
        row.revoked = True
        await db.commit()
    assert (await client.post("/api/v1/auth/refresh", headers=ORIGIN)).status_code == 401
