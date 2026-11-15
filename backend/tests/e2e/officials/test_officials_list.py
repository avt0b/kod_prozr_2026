from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")

IVANOV = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"
ADMIN_ORGAN = "92904ca1-9be8-5b19-befc-8d8f725e914d"


async def _list(client: AsyncClient, **params: str | int) -> Any:
    response = await client.get("/api/v1/officials", params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def test_rating_is_sorted_by_score_desc_by_default(client: AsyncClient) -> None:
    body = await _list(client)

    items = body["items"]
    scores = [i["risk_score"] for i in items]
    assert scores == sorted(scores, reverse=True)
    assert items[0]["id"] == IVANOV
    assert body["total"] == len(items) == 3


async def test_item_matches_contract_shape(client: AsyncClient) -> None:
    items = (await _list(client))["items"]

    top = items[0]
    assert top["position"] == "Начальник отдела"
    assert top["organ"] == "Администрация города Энска"
    assert top["organ_id"] == ADMIN_ORGAN
    assert [f["rule_code"] for f in top["top_flags"]] == ["R01", "R07"]
    assert set(top["top_flags"][0]) >= {"rule_code", "severity"}


async def test_query_filters_by_name_substring(client: AsyncClient) -> None:
    body = await _list(client, query="сидоров")

    assert body["total"] == 1
    assert body["items"][0]["full_name"].startswith("Сидоров")


async def test_organ_filter(client: AsyncClient) -> None:
    body = await _list(client, organ_id=ADMIN_ORGAN)
    items = body["items"]

    assert items and all(i["organ_id"] == ADMIN_ORGAN for i in items)


async def test_min_score_hides_clean_officials(client: AsyncClient) -> None:
    body = await _list(client, min_score=1)
    items = body["items"]

    assert body["total"] == 2
    assert all(i["risk_score"] >= 1 for i in items)


@pytest.mark.parametrize("sort", ["full_name", "-full_name"])
async def test_sort_by_name(client: AsyncClient, sort: str) -> None:
    items = (await _list(client, sort=sort))["items"]

    names = [i["full_name"] for i in items]
    assert names == sorted(names, reverse=sort.startswith("-"))


async def test_sort_by_score_asc(client: AsyncClient) -> None:
    items = (await _list(client, sort="risk_score"))["items"]

    scores = [i["risk_score"] for i in items]
    assert scores == sorted(scores)


async def test_pagination_keeps_total(client: AsyncClient) -> None:
    body = await _list(client, limit=1, offset=1)

    assert body["total"] == 3
    assert len(body["items"]) == 1


async def test_unknown_sort_is_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/officials", params={"sort": "salary"})

    assert response.status_code == 422


async def test_rule_code_keeps_only_officials_with_that_flag(client: AsyncClient) -> None:
    body = await _list(client, rule_code="R01")

    assert [i["id"] for i in body["items"]] == [IVANOV]
    assert body["total"] == 1
    assert (await _list(client, rule_code="R04"))["total"] == 0


async def test_unknown_rule_code_is_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/officials", params={"rule_code": "R99"})
    assert response.status_code == 422
