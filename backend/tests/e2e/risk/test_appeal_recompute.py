from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")

SIDOROV = "ca0f5d74-36ee-5cd1-9b10-fd0cec3423d1"

SPECIFIC = (
    "Сообщаю, что заместитель министра строительства Энской области Сидоров Алексей Николаевич "
    "15.03.2026 получил взятку 2 млн рублей от директора ООО «ГорСтрой» за победу в закупке "
    "№ 0123300000126000045. Готов предоставить переписку и подтвердить показания."
)


async def _official(client: AsyncClient, person_id: str) -> Any:
    return (await client.get(f"/api/v1/officials/{person_id}")).json()


async def _rank(client: AsyncClient, person_id: str) -> int:
    items = (await client.get("/api/v1/officials")).json()["items"]
    return [i["id"] for i in items].index(person_id) + 1


async def test_specific_appeal_raises_score_and_rank_synchronously(client: AsyncClient) -> None:
    before = (await _official(client, SIDOROV))["risk"]["score"]
    rank_before = await _rank(client, SIDOROV)

    response = await client.post("/api/v1/appeals", json={"text": SPECIFIC, "channel": "web"})

    assert response.status_code in (200, 201), response.text
    appeal = response.json()
    assert SIDOROV in appeal["linked_person_ids"]
    profile = await _official(client, SIDOROV)
    r07 = [f for f in profile["risk"]["flags"] if f["rule_code"] == "R07"]
    assert r07, "после обращения должен появиться R07"
    assert profile["risk"]["score"] > before
    assert await _rank(client, SIDOROV) <= rank_before
    assert appeal["id"] in {e["node_id"] for e in r07[0]["evidence"]}


async def test_reanalyze_does_not_duplicate_r07(client: AsyncClient) -> None:
    appeal = (await client.post("/api/v1/appeals", json={"text": SPECIFIC})).json()

    await client.post(f"/api/v1/appeals/{appeal['id']}/reanalyze")
    flags = (await client.get(f"/api/v1/officials/{SIDOROV}/flags")).json()["items"]

    assert [f["rule_code"] for f in flags].count("R07") == 1


async def test_vague_appeal_on_clean_official_gives_only_low_r07(client: AsyncClient) -> None:
    clean = (await client.get("/api/v1/officials", params={"sort": "risk_score"})).json()
    target = clean["items"][0]
    text = f"{target['full_name']} берёт взятки, все об этом знают. Разберитесь уже!"

    appeal = (await client.post("/api/v1/appeals", json={"text": text})).json()

    assert target["id"] in appeal["linked_person_ids"]
    flags = (await client.get(f"/api/v1/officials/{target['id']}/flags")).json()["items"]
    assert [(f["rule_code"], f["severity"]) for f in flags] == [("R07", "low")]
    rank = (await client.get("/api/v1/officials")).json()["items"]
    assert rank[-1]["id"] == target["id"], "ложный донос не выводит в начало рейтинга"
