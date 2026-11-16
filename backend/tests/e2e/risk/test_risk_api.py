from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")

IVANOV = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"


async def _flags(client: AsyncClient, person_id: str) -> Any:
    response = await client.get(f"/api/v1/officials/{person_id}/flags")
    assert response.status_code == 200, response.text
    return response.json()


async def test_scores_are_ready_right_after_seed(client: AsyncClient) -> None:
    officials = (await client.get("/api/v1/officials")).json()["items"]

    assert officials[0]["risk_score"] > 0


async def test_flags_are_sorted_by_weight_and_match_contract(client: AsyncClient) -> None:
    body = await _flags(client, IVANOV)

    weights = [f["weight"] for f in body["items"]]
    assert body["total"] == len(weights) > 0
    assert weights == sorted(weights, reverse=True)
    flag = body["items"][0]
    assert flag["rule_code"] == "R01" and flag["severity"] == "high"
    assert flag["explanation"] and flag["legal_ref"] == "273-ФЗ ст. 10, 11"
    assert set(flag["evidence"][0]) == {"node_id", "type", "label"}


async def test_flag_evidence_points_to_graph_nodes(client: AsyncClient) -> None:
    flags = (await _flags(client, IVANOV))["items"]
    graph = (await client.get(f"/api/v1/officials/{IVANOV}/graph")).json()

    node_ids = {n["id"] for n in graph["nodes"]}
    for flag in flags:
        assert {e["node_id"] for e in flag["evidence"]} <= node_ids, flag["rule_code"]


async def test_recompute_is_idempotent(client: AsyncClient) -> None:
    first = (await client.post("/api/v1/risk/recompute")).json()
    second = (await client.post("/api/v1/risk/recompute")).json()
    flags = (await _flags(client, IVANOV))["items"]

    assert {"officials_processed", "flags_total", "computed_at"} <= set(first)
    assert first["officials_processed"] == second["officials_processed"] == 3
    assert first["flags_total"] == second["flags_total"]
    assert len({f["rule_code"] for f in flags}) == len(flags)


async def test_clean_official_has_no_flags(client: AsyncClient) -> None:
    officials = (await client.get("/api/v1/officials", params={"sort": "risk_score"})).json()
    clean = officials["items"][0]

    assert clean["risk_score"] == 0
    assert (await _flags(client, clean["id"]))["items"] == []


async def test_flags_of_unknown_official_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/officials/{uuid4()}/flags")

    assert response.status_code == 404
