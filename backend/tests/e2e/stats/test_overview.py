from typing import Any

import pytest
from httpx import AsyncClient


async def _overview(client: AsyncClient) -> Any:
    response = await client.get("/api/v1/stats/overview")
    assert response.status_code == 200, response.text
    return response.json()


async def test_overview_on_empty_database_has_all_keys_with_zeros(client: AsyncClient) -> None:
    body = await _overview(client)

    assert body == {
        "officials_total": 0,
        "officials_with_flags": 0,
        "flags_by_severity": {"high": 0, "medium": 0, "low": 0},
        "appeals_total": 0,
        "appeals_by_status": {"new": 0, "analyzed": 0, "routed": 0, "closed": 0},
        "computed_at": None,
    }


@pytest.mark.usefixtures("seeded")
async def test_overview_counts_match_data(client: AsyncClient) -> None:
    body = await _overview(client)
    officials = (await client.get("/api/v1/officials", params={"limit": 100})).json()["items"]
    flags = [
        flag
        for official in officials
        for flag in (await client.get(f"/api/v1/officials/{official['id']}/flags")).json()["items"]
    ]

    assert body["officials_total"] == len(officials) == 3
    assert body["officials_with_flags"] == sum(1 for o in officials if o["risk_score"] > 0)
    for severity, count in body["flags_by_severity"].items():
        assert count == sum(1 for f in flags if f["severity"] == severity)
    assert body["appeals_total"] == 2
    assert body["appeals_by_status"]["analyzed"] == 2
    assert body["computed_at"] is not None
