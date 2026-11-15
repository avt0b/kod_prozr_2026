"""B-20: одно ребро родства на пару людей и докладная без UUID обращений."""

import re

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("seeded")

IVANOV = "b18c4ca3-30e2-56e4-a971-ef71f56e305c"
SPOUSE = "30ad380e-6a1c-5635-98fa-f16d09b2e431"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


@pytest.mark.parametrize("depth", [1, 2, 3])
async def test_spouse_kinship_is_single_edge(client: AsyncClient, depth: int) -> None:
    response = await client.get(f"/api/v1/officials/{IVANOV}/graph", params={"depth": depth})
    assert response.status_code == 200, response.text
    kinship = [e for e in response.json()["edges"] if e["type"] == "kinship"]

    pairs = [frozenset((e["source"], e["target"])) for e in kinship]
    assert len(pairs) == len(set(pairs))
    spouse_edges = [e for e in kinship if {e["source"], e["target"]} == {IVANOV, SPOUSE}]
    assert len(spouse_edges) == 1
    assert spouse_edges[0]["source"] == IVANOV
    assert spouse_edges[0]["label"] == "супруг(а)"


async def test_report_names_appeals_by_number_date_and_category(client: AsyncClient) -> None:
    text = (
        "Иванов Пётр Сергеевич заключил контракт с ООО «СтройРесурс», "
        "которым владеет его жена, на 8 млн рублей 18.04.2023."
    )
    created = await client.post("/api/v1/appeals", json={"text": text, "channel": "web"})
    assert created.status_code == 201, created.text

    response = await client.post("/api/v1/reports", json={"person_id": IVANOV})
    assert response.status_code == 201, response.text
    report = response.json()["text"]

    assert UUID_RE.search(report) is None
    assert created.json()["id"] not in report
    appeal_lines = [line for line in report.splitlines() if line.startswith("— Обращение")]
    assert len(appeal_lines) == 2
    assert all(
        re.match(r"— Обращение № \d+ от \d{2}\.\d{2}\.\d{4} \(категория: [^)]+\): ", line)
        for line in appeal_lines
    )
    assert appeal_lines[0].startswith("— Обращение № 1 ")
    assert any("(категория: закупки)" in line for line in appeal_lines)
