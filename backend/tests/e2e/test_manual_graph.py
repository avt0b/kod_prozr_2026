"""Persistent analyst overlays: ownership, sharing and source-graph isolation."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import Settings
from src.core.infrastructure.auth import issue_access, token_hash
from src.core.infrastructure.database.database import get_async_session_maker
from src.core.infrastructure.database.models.auth import AuthSessionModel, UserModel
from src.modules.manual_graph.infrastructure.models import EdgeModel, NodeModel, WorkspaceModel

ROOT = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"
BASE = "/api/v1/graph-workspaces"


async def test_overlay_access_and_isolation(
    client: AsyncClient, seeded: None, engine: AsyncEngine, test_settings: Settings
) -> None:
    async with get_async_session_maker(engine)() as db:
        viewer = UserModel(username="viewer", password_hash="unused", active=True)
        db.add(viewer)
        await db.flush()
        session = AuthSessionModel(
            user_id=viewer.id,
            refresh_hash=token_hash("test-refresh"),
            logout_hash=token_hash("test-logout"),
            expires_at=datetime.now(UTC) + timedelta(days=1),
            revoked=False,
        )
        db.add(session)
        await db.flush()
        viewer_id = str(viewer.id)
        headers = {"Authorization": "Bearer " + issue_access(viewer, session, test_settings)}
        await db.commit()

    original = (await client.get(f"/api/v1/officials/{ROOT}/graph")).json()
    flags = (await client.get(f"/api/v1/officials/{ROOT}/flags")).json()
    response = await client.post(BASE, json={"title": "Investigation", "official_id": ROOT})
    assert response.status_code == 201, response.text
    workspace = response.json()
    path = f"{BASE}/{workspace['id']}"
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (await client.get(BASE, headers=headers)).json() == []

    response = await client.post(
        path + "/nodes",
        json={"kind": "company", "label": "New company", "notes": "Unverified", "source": "Note"},
    )
    assert response.status_code == 201, response.text
    node = response.json()["nodes"][0]
    assert (await client.get(path)).json()["nodes"][0] == node
    edge = {"source_id": ROOT, "target_id": node["id"], "label": "Analyst link"}
    response = await client.post(path + "/edges", json=edge)
    assert response.status_code == 201, response.text
    edge_id = response.json()["edges"][0]["id"]

    other = (await client.post(BASE, json={"title": "Other", "official_id": ROOT})).json()
    other_path = f"{BASE}/{other['id']}"
    assert (await client.post(other_path + "/edges", json=edge)).status_code == 422
    assert (await client.delete(other_path + f"/nodes/{node['id']}")).status_code == 404
    assert (await client.delete(other_path + f"/edges/{edge_id}")).status_code == 404
    assert (await client.post(path + "/edges", json={**edge, "target_id": ROOT})).status_code == 422
    assert (
        await client.post(path + "/edges", json={**edge, "target_id": str(uuid4())})
    ).status_code == 422
    assert (
        await client.post(path + "/nodes", json={"kind": "company", "label": "   "})
    ).status_code == 422

    response = await client.put(path + "/shares", json={"user_ids": [viewer_id]})
    assert response.status_code == 200, response.text
    shared = (await client.get(path, headers=headers)).json()
    assert shared["can_edit"] is False
    assert shared["nodes"] == [node]
    assert shared["shared_with"] == []
    assert len((await client.get(BASE, headers=headers)).json()) == 1
    forbidden: list[tuple[str, str, dict[str, object] | None]] = [
        ("POST", "/nodes", {"kind": "person", "label": "Forbidden"}),
        ("POST", "/edges", edge),
        ("DELETE", f"/nodes/{node['id']}", None),
        ("DELETE", f"/edges/{edge_id}", None),
        ("PUT", "/shares", {"user_ids": []}),
        ("DELETE", "", None),
    ]
    for method, suffix, payload in forbidden:
        response = await client.request(method, path + suffix, json=payload, headers=headers)
        assert response.status_code == 403, response.text
    await client.put(path + "/shares", json={"user_ids": []})
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (await client.get(BASE, headers=headers)).json() == []

    response = await client.delete(path + f"/nodes/{node['id']}")
    assert response.json()["nodes"] == []
    assert response.json()["edges"] == []
    assert (await client.get(f"/api/v1/officials/{ROOT}/graph")).json() == original
    assert (await client.get(f"/api/v1/officials/{ROOT}/flags")).json() == flags
    assert (await client.delete(path)).status_code == 204
    assert (await client.get(path)).status_code == 404


async def test_workspace_validation(client: AsyncClient, seeded: None) -> None:
    assert (
        await client.post(BASE, json={"title": "Missing", "official_id": str(uuid4())})
    ).status_code == 404
    response = await client.post(BASE, json={"title": "Test", "official_id": ROOT})
    path = f"{BASE}/{response.json()['id']}"
    assert (
        await client.put(path + "/shares", json={"user_ids": [str(uuid4())]})
    ).status_code == 422
    assert (
        await client.post(path + "/nodes", json={"kind": "unknown", "label": "Invalid"})
    ).status_code == 422


async def test_read_waits_for_workspace_write(
    client: AsyncClient, seeded: None, engine: AsyncEngine
) -> None:
    response = await client.post(BASE, json={"title": "Concurrent", "official_id": ROOT})
    identifier = UUID(response.json()["id"])
    async with get_async_session_maker(engine)() as db:
        await db.get(WorkspaceModel, identifier, with_for_update=True)
        pending = asyncio.create_task(client.get(f"{BASE}/{identifier}"))
        try:
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), timeout=0.2)
            node = NodeModel(workspace_id=identifier, kind="person", label="New")
            db.add(node)
            await db.flush()
            db.add(
                EdgeModel(
                    workspace_id=identifier, source_id=UUID(ROOT), target_id=node.id, label="Link"
                )
            )
            await db.commit()
            result = (await asyncio.wait_for(pending, timeout=5)).json()
            assert len(result["nodes"]) == 1
            assert result["edges"][0]["target_id"] == result["nodes"][0]["id"]
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
