from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")

IVANOV = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"
SPOUSE = "30ad380e-6a1c-5635-98fa-f16d09b2e431"
STROYRESURS = "749cc21a-1319-57ed-b4d4-39f5e519c7a8"


async def _profile(client: AsyncClient, person_id: str) -> Any:
    response = await client.get(f"/api/v1/officials/{person_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def test_profile_has_contract_sections(client: AsyncClient) -> None:
    profile = await _profile(client, IVANOV)

    assert set(profile) >= {"person", "appointments", "authorities", "relatives", "companies"}
    appointment = profile["appointments"][0]
    assert {"person_id", "position_id", "position", "organ"} <= set(appointment)
    assert profile["authorities"][0]["kind"] == "procurement"
    assert profile["authorities"][0]["scope"]["okpd2"] == ["41.20", "42"]


async def test_profile_shows_spouse_and_her_company_with_contracts(client: AsyncClient) -> None:
    profile = await _profile(client, IVANOV)

    assert [(r["kind"], r["person"]["id"]) for r in profile["relatives"]] == [("spouse", SPOUSE)]
    link = next(c for c in profile["companies"] if c["company"]["id"] == STROYRESURS)
    assert link["role"] == "founder"
    assert link["relation"] == "spouse"
    assert link["via_person_id"] == SPOUSE
    assert link["contracts_count"] == 2
    assert link["contracts_amount"] == 12_500_000


async def test_profile_risk_flags_carry_evidence_with_graph_node_ids(client: AsyncClient) -> None:
    profile = await _profile(client, IVANOV)
    graph = (await client.get(f"/api/v1/officials/{IVANOV}/graph")).json()

    risk = profile["risk"]
    assert risk["score"] > 0 and risk["computed_at"]
    r01 = next(f for f in risk["flags"] if f["rule_code"] == "R01")
    node_ids = {n["id"] for n in graph["nodes"]}
    assert r01["evidence"] and all(e["node_id"] in node_ids for e in r01["evidence"])


async def test_unknown_official_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/officials/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["title"] == "OfficialNotFoundError"


async def test_organs_list(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/organs")).json()

    assert body["total"] == 2
    assert {"id", "name", "inn", "region"} <= set(body["items"][0])
