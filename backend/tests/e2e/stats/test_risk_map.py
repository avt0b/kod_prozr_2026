from typing import Any

import pytest
from httpx import AsyncClient


async def _risk_map(client: AsyncClient, **params: Any) -> Any:
    response = await client.get("/api/v1/risk-map", params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def test_risk_map_on_empty_database(client: AsyncClient) -> None:
    assert await _risk_map(client) == {"items": [], "total": 0, "organs": [], "computed_at": None}


@pytest.mark.usefixtures("seeded")
async def test_risk_map_aggregates_positions_from_rating(client: AsyncClient) -> None:
    body = await _risk_map(client)
    rating = (await client.get("/api/v1/officials", params={"limit": 100})).json()["items"]
    scores = {o["full_name"]: o["risk_score"] for o in rating}

    assert body["total"] == len(body["items"]) == 3
    assert body["computed_at"] is not None
    assert sum(i["officials_total"] for i in body["items"]) == len(rating)
    by_title = {(i["title"], i["department"]): i for i in body["items"]}

    # Иванов: начальник отдела закупок с полномочием procurement, флаги R01 и R07.
    buyer = by_title[("Начальник отдела", "Отдел муниципальных закупок")]
    assert body["items"][0] == buyer  # самый высокий средний балл — сверху
    assert buyer["authorities"] == ["procurement"]
    assert buyer["risk_level"] == "high"
    assert buyer["officials_total"] == buyer["officials_with_flags"] == 1
    assert buyer["flagged_share"] == 1.0
    assert buyer["max_score"] == buyer["avg_score"] == scores["Иванов Пётр Сергеевич"]
    assert {"R01", "R07"} <= {r["rule_code"] for r in buyer["top_rules"]}
    assert buyer["top_officials"][0]["full_name"] == "Иванов Пётр Сергеевич"
    assert any("R01" in r["rule_codes"] for r in buyer["typical_risks"])
    assert all(r["legal_ref"] for r in buyer["typical_risks"])

    # Чистый служащий кадровой службы: риск должности средний, флагов нет.
    hr = by_title[("Главный специалист", "Отдел кадров")]
    assert hr["risk_level"] == "medium"
    assert hr["officials_with_flags"] == 0 and hr["avg_score"] == 0.0
    assert hr["top_rules"] == [] and hr["top_officials"] == []
    assert [r["authority"] for r in hr["typical_risks"]] == ["hr"]

    organs = {o["organ"]: o for o in body["organs"]}
    assert set(organs) == {
        "Администрация города Энска",
        "Министерство строительства Энской области",
    }
    city = organs["Администрация города Энска"]
    assert city["positions_total"] == 2 and city["officials_total"] == 2
    assert city["officials_with_flags"] == 1 and city["flagged_share"] == 0.5


@pytest.mark.usefixtures("seeded")
async def test_risk_map_filters_by_organ_and_validates_limit(client: AsyncClient) -> None:
    organs = (await client.get("/api/v1/organs")).json()["items"]
    ministry = next(o for o in organs if o["name"].startswith("Министерство"))

    body = await _risk_map(client, organ_id=ministry["id"])

    assert body["total"] == 1
    assert body["items"][0]["organ_id"] == ministry["id"]
    assert body["items"][0]["authorities"] == ["permits"]
    assert [o["organ_id"] for o in body["organs"]] == [ministry["id"]]
    assert (await _risk_map(client, limit=1, offset=2))["total"] == 3
    assert (await client.get("/api/v1/risk-map", params={"limit": 1000})).status_code == 422
