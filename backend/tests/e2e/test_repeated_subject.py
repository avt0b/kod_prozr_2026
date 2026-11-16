"""E2E AI-04: repeated_subject ставит код по другим обращениям в Postgres (ai.md §2)."""

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")

SIDOROV = "ca0f5d74-36ee-5cd1-9b10-fd0cec3423d1"
FIRST = (
    "Заместитель министра строительства Энской области Сидоров Алексей Николаевич "
    "15.03.2026 получил взятку 2 млн рублей за победу в закупке."
)
SECOND = "Сидоров Алексей Николаевич снова берёт взятки, разберитесь!"
COMPANY_1 = "Подрядчик ООО «Вектор-Плюс» выигрывает все аукционы в министерстве через откат."
COMPANY_2 = "Опять аукцион выиграла фирма «Вектор-плюс», откат известен всем."


def codes(appeal: dict[str, Any]) -> set[str]:
    return {s["code"] for s in appeal["analysis"]["signals"]}


async def post(client: AsyncClient, text: str) -> dict[str, Any]:
    response = await client.post("/api/v1/appeals", json={"text": text, "channel": "web"})
    assert response.status_code in (200, 201), response.text
    result: dict[str, Any] = response.json()
    return result


async def test_second_appeal_on_same_official_is_repeated(client: AsyncClient) -> None:
    first = await post(client, FIRST)
    second = await post(client, SECOND)

    assert SIDOROV in first["linked_person_ids"] and SIDOROV in second["linked_person_ids"]
    assert "repeated_subject" not in codes(first)
    assert "repeated_subject" in codes(second)
    signal = next(s for s in second["analysis"]["signals"] if s["code"] == "repeated_subject")
    assert signal["text"] == "служащий уже упоминался в других обращениях за 12 месяцев: 1"
    # Повтор — не факт из текста: расплывчатое обращение остаётся расплывчатым.
    assert "vague_no_facts" in codes(second)
    assert second["analysis"]["specificity"] == 0.15

    stored = (await client.get(f"/api/v1/appeals/{second['id']}")).json()
    assert "repeated_subject" in codes(stored)


async def test_reanalyze_counts_only_earlier_appeals(client: AsyncClient) -> None:
    first = await post(client, FIRST)
    await post(client, SECOND)

    again = (await client.post(f"/api/v1/appeals/{first['id']}/reanalyze")).json()

    assert "repeated_subject" not in codes(again), "более позднее обращение не делает повтор"


async def test_same_company_is_repeated_without_official(client: AsyncClient) -> None:
    first = await post(client, COMPANY_1)
    second = await post(client, COMPANY_2)

    assert not second["linked_person_ids"]
    assert "repeated_subject" not in codes(first)
    assert "repeated_subject" in codes(second)
