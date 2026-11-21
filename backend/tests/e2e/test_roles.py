"""Матрица доступа ролей гражданин / аналитик / администратор (#70)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.infrastructure.auth import password_hasher
from src.core.infrastructure.database.database import get_async_session_maker
from src.core.infrastructure.database.models.auth import Role, UserModel

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "role-test-password"
TEXT = (
    "Начальник отдела Иванов требует деньги за ускорение выдачи разрешения "
    "на строительство, передача наличными у здания администрации."
)


async def add_user(engine: AsyncEngine, username: str, role: Role) -> None:
    async with get_async_session_maker(engine)() as db:
        db.add(
            UserModel(
                username=username,
                password_hash=password_hasher.hash(PASSWORD),
                active=True,
                role=role,
            )
        )
        await db.commit()


async def login(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
        headers=ORIGIN,
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def register(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        # Роль из тела игнорируется: саморегистрация даёт только гражданина.
        json={"username": username, "password": PASSWORD, "role": "admin"},
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    assert response.json()["user"]["role"] == "citizen"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_citizen_submits_and_sees_only_own_appeals(client: AsyncClient) -> None:
    analyst = dict(client.headers)
    client.headers.pop("Authorization")
    citizen = await register(client, "ivan.citizen")
    other = await register(client, "petr.citizen")

    me = await client.get("/api/v1/auth/me", headers=citizen)
    assert me.json()["role"] == "citizen"

    created = await client.post("/api/v1/citizen/appeals", json={"text": TEXT}, headers=citizen)
    assert created.status_code == 201, created.text
    body = created.json()
    assert set(body) == {"id", "received_at", "text", "status"}  # без анализа и служащих
    assert body["status"] == "analyzed"

    mine = (await client.get("/api/v1/citizen/appeals", headers=citizen)).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == body["id"]
    assert (await client.get("/api/v1/citizen/appeals", headers=other)).json()["total"] == 0

    # Аналитик видит обращение гражданина и рассматривает его — гражданин видит статус.
    routed = await client.post(
        f"/api/v1/appeals/{body['id']}/status", json={"status": "routed"}, headers=analyst
    )
    assert routed.status_code == 200, routed.text
    assert routed.json()["status"] == "routed"
    mine = (await client.get("/api/v1/citizen/appeals", headers=citizen)).json()
    assert mine["items"][0]["status"] == "routed"
    closed = await client.post(
        f"/api/v1/appeals/{body['id']}/status", json={"status": "closed"}, headers=analyst
    )
    assert closed.json()["status"] == "closed"
    again = await client.post(
        f"/api/v1/appeals/{body['id']}/status", json={"status": "routed"}, headers=analyst
    )
    assert again.status_code == 409


async def test_citizen_has_no_access_to_workspace_or_admin(client: AsyncClient) -> None:
    client.headers.pop("Authorization")
    citizen = await register(client, "anna.citizen")
    for method, path in [
        ("GET", "/api/v1/officials"),
        ("GET", "/api/v1/appeals"),
        ("POST", "/api/v1/appeals"),
        ("GET", "/api/v1/stats/overview"),
        ("GET", "/api/v1/graph-workspaces"),
        ("GET", "/api/v1/admin/users"),
    ]:
        response = await client.request(method, path, headers=citizen, json={"text": TEXT})
        assert response.status_code == 403, (method, path, response.status_code)


async def test_analyst_has_no_access_to_admin_or_citizen_cabinet(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/officials")).status_code == 200
    assert (await client.get("/api/v1/admin/users")).status_code == 403
    assert (await client.get("/api/v1/citizen/appeals")).status_code == 403
    assert (await client.post("/api/v1/citizen/appeals", json={"text": TEXT})).status_code == 403


async def test_register_rejects_taken_login(client: AsyncClient) -> None:
    client.headers.pop("Authorization")
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "Test-Analyst", "password": PASSWORD},
        headers=ORIGIN,
    )
    assert response.status_code == 409


async def test_admin_manages_analysts(client: AsyncClient, engine: AsyncEngine) -> None:
    await add_user(engine, "root", Role.ADMIN)
    admin = await login(client, "root")
    assert (await client.get("/api/v1/officials", headers=admin)).status_code == 200

    created = await client.post(
        "/api/v1/admin/users",
        json={"username": "New.Analyst", "password": PASSWORD, "role": "analyst"},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user == {**user, "username": "new.analyst", "role": "analyst", "active": True}
    duplicate = await client.post(
        "/api/v1/admin/users",
        json={"username": "new.analyst", "password": PASSWORD},
        headers=admin,
    )
    assert duplicate.status_code == 409

    listed = (await client.get("/api/v1/admin/users?role=analyst", headers=admin)).json()
    assert {u["username"] for u in listed["items"]} == {"test-analyst", "new.analyst"}
    found = (await client.get("/api/v1/admin/users?query=new", headers=admin)).json()
    assert found["total"] == 1

    analyst = await login(client, "new.analyst")
    blocked = await client.patch(
        f"/api/v1/admin/users/{user['id']}", json={"active": False}, headers=admin
    )
    assert blocked.json()["active"] is False
    # Блокировка отзывает уже выданный токен и запрещает вход.
    assert (await client.get("/api/v1/officials", headers=analyst)).status_code == 401
    relogin = await client.post(
        "/api/v1/auth/login",
        json={"username": "new.analyst", "password": PASSWORD},
        headers=ORIGIN,
    )
    assert relogin.status_code == 401

    promoted = await client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"active": True, "role": "admin"},
        headers=admin,
    )
    assert promoted.json()["role"] == "admin"

    assert (
        await client.delete(f"/api/v1/admin/users/{user['id']}", headers=admin)
    ).status_code == 204
    assert (
        await client.delete(f"/api/v1/admin/users/{user['id']}", headers=admin)
    ).status_code == 404


async def test_last_admin_cannot_be_removed(client: AsyncClient, engine: AsyncEngine) -> None:
    await add_user(engine, "root", Role.ADMIN)
    admin = await login(client, "root")
    me = (await client.get("/api/v1/auth/me", headers=admin)).json()
    demote = await client.patch(
        f"/api/v1/admin/users/{me['id']}", json={"role": "analyst"}, headers=admin
    )
    assert demote.status_code == 409
    block = await client.patch(
        f"/api/v1/admin/users/{me['id']}", json={"active": False}, headers=admin
    )
    assert block.status_code == 409
    assert (
        await client.delete(f"/api/v1/admin/users/{me['id']}", headers=admin)
    ).status_code == 409

    await add_user(engine, "root2", Role.ADMIN)
    assert (
        await client.patch(
            f"/api/v1/admin/users/{me['id']}", json={"role": "analyst"}, headers=admin
        )
    ).status_code == 200
    # Смена роли отзывает сессии: старый токен больше не действует.
    assert (await client.get("/api/v1/auth/me", headers=admin)).status_code == 401


async def test_graph_workspace_cannot_be_shared_with_citizen(
    client: AsyncClient, seeded: None
) -> None:
    analyst = dict(client.headers)
    client.headers.pop("Authorization")
    citizen = await register(client, "olga.citizen")
    citizen_id = (await client.get("/api/v1/auth/me", headers=citizen)).json()["id"]
    found = await client.get("/api/v1/graph-workspaces/users?query=olga", headers=analyst)
    assert found.json() == []

    officials = (await client.get("/api/v1/officials?limit=1", headers=analyst)).json()
    workspace = await client.post(
        "/api/v1/graph-workspaces",
        json={"official_id": officials["items"][0]["id"], "title": "Проверка"},
        headers=analyst,
    )
    assert workspace.status_code == 201, workspace.text
    shared = await client.put(
        f"/api/v1/graph-workspaces/{workspace.json()['id']}/shares",
        json={"user_ids": [citizen_id]},
        headers=analyst,
    )
    assert shared.status_code == 422
