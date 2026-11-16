from uuid import uuid4

from httpx import AsyncClient

PERSON = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"


async def test_analyst_actions_are_visible_in_profile_journal(
    client: AsyncClient, seeded: None
) -> None:
    before = (await client.get(f"/api/v1/audit?object_id={PERSON}")).json()["total"]
    assert (await client.get(f"/api/v1/officials/{PERSON}")).status_code == 200
    assert (await client.post("/api/v1/reports", json={"person_id": PERSON})).status_code == 201
    assert (
        await client.post(
            "/api/v1/appeals",
            json={"text": "Иванов Пётр Сергеевич требует взятку 5000 рублей.", "channel": "web"},
        )
    ).status_code == 201
    assert (await client.post("/api/v1/risk/recompute")).status_code == 200
    response = await client.get(f"/api/v1/audit?object_id={PERSON}&limit=100")
    assert response.status_code == 200
    log = response.json()
    assert log["total"] > before
    assert {a["action"] for a in log["items"]} >= {
        "open_profile",
        "create_report",
        "submit_appeal",
        "recompute_risk",
    }
    assert all(a["actor"] == "analyst" and a["object_id"] == PERSON for a in log["items"])
    page = (await client.get(f"/api/v1/audit?object_id={PERSON}&limit=1&offset=1")).json()
    assert len(page["items"]) == 1
    assert page["total"] == log["total"]
    assert (await client.get("/api/v1/audit?limit=101")).status_code == 422


async def test_failed_operations_do_not_enter_journal(client: AsyncClient, seeded: None) -> None:
    before = (await client.get("/api/v1/audit")).json()["total"]
    assert (await client.get(f"/api/v1/officials/{uuid4()}")).status_code == 404
    assert (
        await client.post("/api/v1/reports", json={"person_id": str(uuid4())})
    ).status_code == 404
    assert (await client.post("/api/v1/appeals", json={"text": "   "})).status_code == 422
    assert (await client.get("/api/v1/audit")).json()["total"] == before
