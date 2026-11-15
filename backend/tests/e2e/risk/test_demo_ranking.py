"""E2E на полном наборе data/generated: порядок рейтинга из docs/demo.md (B-17, ADR-16).

Фоллбэк без LLM, как в CI и smoke: сиды -> пересчёт с R08 -> демо-обращение H1.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import Settings
from src.core.infrastructure.database.database import get_async_session_maker
from src.seed.loader import load_seed

ROOT = Path(__file__).resolve().parents[4]
GENERATED = ROOT / "data" / "generated"
DEMO_TEXT = ROOT / "demo" / "appeal_h1.txt"
MARGIN = 5

pytestmark = pytest.mark.skipif(
    not (GENERATED / "_truth" / "meta.json").is_file() or not DEMO_TEXT.is_file(),
    reason="нет data/generated или demo/appeal_h1.txt",
)


def _truth() -> tuple[dict[str, str], set[str]]:
    cases: dict[str, str] = json.loads((GENERATED / "_truth" / "meta.json").read_text())["cases"]
    schemes = json.loads((GENERATED / "_truth" / "schemes.json").read_text())
    positive = {s["person_id"] for s in schemes if s.get("person_id") and s["rule_codes"]}
    return cases, positive


async def _ranking(client: AsyncClient, rule_code: str | None = None) -> list[dict[str, Any]]:
    query = f"&rule_code={rule_code}" if rule_code else ""
    response = await client.get(f"/api/v1/officials?limit=100{query}")
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def _rank(items: list[dict[str, Any]], person_id: str) -> int:
    return [i["id"] for i in items].index(person_id) + 1


@pytest.fixture
async def full_seed(engine: AsyncEngine, test_settings: Settings) -> None:
    async with get_async_session_maker(engine)() as session:
        await load_seed(session, GENERATED, test_settings)


@pytest.mark.usefixtures("full_seed")
async def test_demo_order_on_full_generated_data(client: AsyncClient) -> None:
    cases, positive = _truth()
    h1 = cases["H1"]

    before = await _ranking(client)
    scores = [i["risk_score"] for i in before]
    assert _rank(before, h1) == 3, [(i["full_name"], i["risk_score"]) for i in before[:5]]
    assert scores[1] - scores[2] >= MARGIN  # ниже двух схем с запасом
    assert scores[2] - scores[3] >= MARGIN  # и выше следующего кейса

    # C2 и C5 — в общем топ-10; C2–C5 — в топ-3 при фильтре по своему правилу (demo.md, 3:40).
    top10 = {i["id"] for i in before[:10]}
    assert {cases["C2"], cases["C5"]} <= top10
    for case, rule in (("C2", "R02"), ("C3", "R03"), ("C4", "R04"), ("C5", "R05")):
        assert _rank(await _ranking(client, rule), cases[case]) <= 3, case
    assert cases["C6"] in {i["id"] for i in await _ranking(client, "R08")}

    clean = [i for i in before if i["id"] not in positive]
    assert max(i["risk_score"] for i in clean) <= 40

    response = await client.post(
        "/api/v1/appeals", json={"text": DEMO_TEXT.read_text("utf-8").strip(), "channel": "web"}
    )
    assert response.status_code == 201, response.text
    assert h1 in response.json()["linked_person_ids"]

    after = await _ranking(client)
    assert after[0]["id"] == h1
    assert after[0]["risk_score"] - after[1]["risk_score"] >= MARGIN
    assert after[0]["risk_score"] > scores[2]
