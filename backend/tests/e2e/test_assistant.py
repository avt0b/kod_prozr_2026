import json
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import BASE_DIR, Settings
from src.core.infrastructure.database.database import get_async_session_maker
from src.modules.officials.infrastructure.database.models import PersonModel
from src.seed.loader import load_seed

pytestmark = pytest.mark.usefixtures("seeded")
PERSON = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"


async def test_assistant_r01_returns_real_person_and_does_not_write(client: AsyncClient) -> None:
    before = (await client.get("/api/v1/audit")).json()["total"]
    response = await client.post(
        "/api/v1/assistant/ask",
        json={"question": "Покажи служащих, у которых родственники среди подрядчиков их органа"},
    )
    assert response.status_code == 200
    answer = response.json()
    assert {s["id"] for s in answer["sources"]} == {PERSON}
    assert "Иванов" in answer["answer"] and "R01" in answer["answer"]
    assert (await client.get("/api/v1/audit")).json()["total"] == before


async def test_assistant_top_profile_appeals_company_and_unknown(client: AsyncClient) -> None:
    questions = [
        ("Кто с самым высоким риском и почему?", "person"),
        (f"Профиль {PERSON}", "person"),
        ("Найди служащего Иванов", "person"),
        ("Какие обращения поступали на Иванова?", "appeal"),
        ("Найди компанию «СтройРесурс»", "company"),
    ]
    for question, expected in questions:
        response = await client.post("/api/v1/assistant/ask", json={"question": question})
        assert response.status_code == 200
        answer = response.json()
        assert answer["sources"], (question, answer)
        assert len(answer["sources"]) <= 20
        for source in answer["sources"]:
            assert source["type"] == expected
            UUID(source["id"])
    unknown = (
        await client.post("/api/v1/assistant/ask", json={"question": "Какая погода?"})
    ).json()
    assert unknown["sources"] == []
    assert "Не могу ответить" in unknown["answer"]


async def test_assistant_h1_on_sokolov_fixture(
    client: AsyncClient, engine: AsyncEngine, test_settings: Settings, tmp_path: Path
) -> None:
    for path in (BASE_DIR / "data/example").glob("*.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    path = tmp_path / "persons.json"
    persons = json.loads(path.read_text())
    persons[0]["full_name"] = "Соколов Андрей Викторович"
    persons[1]["full_name"] = "Соколова Марина Олеговна"
    path.write_text(json.dumps(persons))
    async with get_async_session_maker(engine)() as session:
        await load_seed(session, tmp_path, test_settings)
    answer = (
        await client.post(
            "/api/v1/assistant/ask",
            json={
                "question": "Покажи служащих, у которых родственники среди подрядчиков их органа"
            },
        )
    ).json()
    assert "Соколов Андрей Викторович" in answer["answer"]
    assert PERSON in {s["id"] for s in answer["sources"]}


async def test_scoped_top_and_ambiguous_surname(client: AsyncClient, engine: AsyncEngine) -> None:
    profile = (await client.get(f"/api/v1/officials/{PERSON}")).json()
    organ = profile["appointments"][0]["organ"]
    answer = (
        await client.post(
            "/api/v1/assistant/ask",
            json={"question": f"Кто в {organ['name']} с самым высоким риском и почему?"},
        )
    ).json()
    expected = (await client.get("/api/v1/officials", params={"organ_id": organ["id"]})).json()
    assert answer["sources"]
    assert {s["id"] for s in answer["sources"]} <= {p["id"] for p in expected["items"]}
    # Two real officials with the same surname must not be silently resolved to one.
    from_id = UUID("8b2f6756-4fdc-5517-afd0-c6d6a79f855e")
    async with get_async_session_maker(engine)() as session:
        person = await session.get(PersonModel, from_id)
        assert person is not None
        person.full_name = "Иванов Павел Сергеевич"
        await session.commit()
    answer = (
        await client.post(
            "/api/v1/assistant/ask", json={"question": "Какие обращения поступали на Иванова?"}
        )
    ).json()
    assert answer["sources"] == []
    assert "Уточните" in answer["answer"]
