import json
from collections.abc import Generator
from pathlib import Path
from time import perf_counter
from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.config import BASE_DIR, get_settings_from_env
from src.seed.__main__ import run


@pytest.fixture(autouse=True)
def setup_misha(
    seeded: None, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LLM_BASE_URL", "")
    get_settings_from_env.cache_clear()
    yield
    get_settings_from_env.cache_clear()


@pytest.fixture
def seed_dir(tmp_path: Path) -> Path:
    for source in (BASE_DIR / "data/example").glob("*.json"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    return tmp_path


PERSON_ID = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"
TEXT = (
    "Иванов Пётр Сергеевич заключил контракт с ООО «СтройРесурс», "
    "которым владеет его жена, на 8 млн рублей 18.04.2023."
)


async def test_appeal_graph_report_flow(client: AsyncClient) -> None:
    response = await client.post("/api/v1/appeals", json={"text": TEXT, "channel": "web"})
    assert response.status_code == 201, response.text
    appeal = response.json()
    assert appeal["status"] == "analyzed"
    assert appeal["analysis"]["is_corruption"] is True
    assert appeal["linked_person_ids"] == [PERSON_ID]
    assert appeal["linked_persons"][0]["full_name"] == "Иванов Пётр Сергеевич"
    assert appeal["linked_persons"][0]["position"]
    assert appeal["linked_persons"][0]["organ"]
    assert appeal["linked_persons"][0]["risk_score"] > 0
    appeal_id = appeal["id"]
    response = await client.post(f"/api/v1/appeals/{appeal_id}/reanalyze")
    assert response.status_code == 200, response.text
    assert response.json()["linked_person_ids"] == [PERSON_ID]
    response = await client.get("/api/v1/appeals?status=analyzed&category=procurement&limit=1")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    graph = (await client.get(f"/api/v1/officials/{PERSON_ID}/graph")).json()
    nodes = {node["id"]: node for node in graph["nodes"]}
    flags = (await client.get(f"/api/v1/officials/{PERSON_ID}/flags")).json()["items"]
    for flag in flags:
        assert all(e["node_id"] in nodes for e in flag["evidence"])
    contract_nodes = [n for n in nodes.values() if n["type"] == "contract"]
    assert len(contract_nodes) == 1
    assert "3 контрактов" in contract_nodes[0]["label"]
    response = await client.post("/api/v1/reports", json={"person_id": PERSON_ID})
    assert response.status_code == 201, response.text
    report = response.json()
    assert "Сформировано автоматически. Решение принимает уполномоченное лицо" in report["text"]
    assert "Полномочия:" in report["text"]
    assert "Связанные обращения граждан: 2" in report["text"]
    assert all(flag["rule_code"] in report["text"] for flag in flags)
    assert (await client.get(f"/api/v1/reports/{report['id']}")).json() == report


async def test_validation_and_missing_objects(client: AsyncClient) -> None:
    for path in ("appeals", "reports", "officials"):
        response = await client.get(f"/api/v1/{path}/{uuid4()}")
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/problem+json")
    assert (await client.post("/api/v1/appeals", json={"text": "   "})).status_code == 422
    assert (await client.get("/api/v1/appeals?limit=101")).status_code == 422
    assert (await client.get(f"/api/v1/officials/{PERSON_ID}/graph?depth=4")).status_code == 422


async def test_reseed_removes_stale_data(client: AsyncClient, seed_dir: Path) -> None:
    await client.post("/api/v1/appeals", json={"text": TEXT})
    report = (await client.post("/api/v1/reports", json={"person_id": PERSON_ID})).json()
    (seed_dir / "_truth").mkdir()
    (seed_dir / "_truth" / "schemes.json").write_text("not domain JSON")
    await run(seed_dir, analyze=True, recompute=True)
    await run(seed_dir, analyze=True, recompute=True)
    assert (await client.get("/api/v1/appeals")).json()["total"] == 2
    assert (await client.get(f"/api/v1/reports/{report['id']}")).status_code == 404


async def test_invalid_seed_preserves_existing_data(client: AsyncClient, seed_dir: Path) -> None:
    (seed_dir / "contracts.json").write_text('[{"id": "invalid"}]')
    with pytest.raises(ValueError, match=r"contracts.json: record 1"):
        await run(seed_dir, analyze=True, recompute=True)
    assert (await client.get("/api/v1/appeals")).json()["total"] == 2


async def test_seed_failure_rolls_back_all_modules(
    client: AsyncClient, seed_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail(*args: object, **kwargs: object) -> dict[str, int]:
        raise RuntimeError("simulated import failure")

    # A newly created appeal must survive TRUNCATE + committed officials savepoint.
    appeal = (await client.post("/api/v1/appeals", json={"text": TEXT})).json()
    monkeypatch.setattr("src.seed.loader.seed_counterparties", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        await run(seed_dir, analyze=True, recompute=True)
    assert (await client.get(f"/api/v1/appeals/{appeal['id']}")).status_code == 200
    assert (await client.get(f"/api/v1/officials/{PERSON_ID}")).status_code == 200


async def test_full_volume_seed_and_graph(client: AsyncClient, seed_dir: Path) -> None:
    def read(name: str) -> list[dict[str, object]]:
        return cast(list[dict[str, object]], json.loads((seed_dir / f"{name}.json").read_text()))

    def write(name: str, rows: list[dict[str, object]]) -> None:
        (seed_dir / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False))

    persons, appointments = read("persons"), read("appointments")
    for index in range(147):
        person_id = str(uuid4())
        persons.append({**persons[0], "id": person_id, "full_name": f"Служащий {index}"})
        appointments.append({**appointments[0], "id": str(uuid4()), "person_id": person_id})
    contracts = read("contracts")
    contracts += [{**contracts[0], "id": str(uuid4())} for _ in range(1997)]
    appeals = read("appeals")
    appeals += [{**appeals[1], "id": str(uuid4())} for _ in range(98)]
    for name, rows in (
        ("persons", persons),
        ("appointments", appointments),
        ("contracts", contracts),
        ("appeals", appeals),
    ):
        write(name, rows)
    started = perf_counter()
    await run(seed_dir, analyze=True, recompute=True)
    assert perf_counter() - started < 60
    started = perf_counter()
    response = await client.get(f"/api/v1/officials/{PERSON_ID}/graph")
    elapsed = perf_counter() - started
    assert response.status_code == 200
    graph = response.json()
    assert graph["truncated"] is False
    assert len([n for n in graph["nodes"] if n["type"] == "contract"]) == 1
    assert "2000 контрактов" in next(n["label"] for n in graph["nodes"] if n["type"] == "contract")
    assert elapsed < 0.3


async def test_h1_demo_links_sokolov_and_shows_full_chain(
    client: AsyncClient, seed_dir: Path
) -> None:
    persons_path = seed_dir / "persons.json"
    persons = json.loads(persons_path.read_text())
    persons[0]["full_name"] = "Соколов Андрей Викторович"
    persons[1]["full_name"] = "Соколова Марина Олеговна"
    persons_path.write_text(json.dumps(persons, ensure_ascii=False))
    companies_path = seed_dir / "companies.json"
    companies = json.loads(companies_path.read_text())
    companies[0]["name"] = "ООО «ДорСтройРесурс»"
    companies_path.write_text(json.dumps(companies, ensure_ascii=False))
    await run(seed_dir, analyze=True, recompute=True)
    response = await client.post(
        "/api/v1/appeals",
        json={
            "text": "Здравствуйте. Хочу сообщить о ситуации в департаменте строительства и "
            "дорожного хозяйства. Начальник отдела закупок Соколов Андрей Викторович уже второй "
            "год отдаёт контракты на ремонт дорог фирме «ДорСтройРесурс», которая принадлежит его "
            "жене. В марте 2026 года им снова дали контракт на 9,5 млн рублей "
            "без всякого конкурса. "
            "Другие подрядчики даже не могут подать заявки. Прошу разобраться."
        },
    )
    assert response.status_code == 201
    assert response.json()["linked_person_ids"] == [PERSON_ID]
    graph = (await client.get(f"/api/v1/officials/{PERSON_ID}/graph")).json()
    nodes = {n["id"]: n for n in graph["nodes"]}
    flags = (await client.get(f"/api/v1/officials/{PERSON_ID}/flags")).json()["items"]
    evidence = next(f["evidence"] for f in flags if f["rule_code"] == "R01")
    assert [nodes[e["node_id"]]["type"] for e in evidence] == [
        "person",
        "person",
        "company",
        "contract",
        "organ",
    ]
    assert nodes[evidence[0]["node_id"]]["label"] == "Соколов Андрей Викторович"
    assert nodes[evidence[1]["node_id"]]["label"] == "Соколова Марина Олеговна"
    assert nodes[evidence[2]["node_id"]]["label"] == "ООО «ДорСтройРесурс»"
    pairs = {(e["source"], e["target"]) for e in graph["edges"]}
    assert all((a["node_id"], b["node_id"]) in pairs for a, b in zip(evidence, evidence[1:]))


async def test_graph_reports_truncation_without_dangling_edges(
    client: AsyncClient, seed_dir: Path
) -> None:
    companies_path = seed_dir / "companies.json"
    roles_path = seed_dir / "company_roles.json"
    companies = json.loads(companies_path.read_text())
    roles = json.loads(roles_path.read_text())
    for _ in range(160):
        company_id = str(uuid4())
        companies.append({**companies[0], "id": company_id})
        roles.append(
            {**roles[0], "id": str(uuid4()), "company_id": company_id, "person_id": PERSON_ID}
        )
    companies_path.write_text(json.dumps(companies))
    roles_path.write_text(json.dumps(roles))
    await run(seed_dir, analyze=True, recompute=True)
    graph = (await client.get(f"/api/v1/officials/{PERSON_ID}/graph")).json()
    assert graph["truncated"] is True
    assert len(graph["nodes"]) == 150
    ids = {node["id"] for node in graph["nodes"]}
    assert all(edge["source"] in ids and edge["target"] in ids for edge in graph["edges"])
