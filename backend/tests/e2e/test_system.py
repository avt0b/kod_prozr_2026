from uuid import uuid4

from httpx import AsyncClient


async def test_health_returns_ok_when_database_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unknown_official_returns_problem_details_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/officials/{uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "OfficialNotFoundError"
    assert body["status"] == 404
    assert body["detail"] == "Служащий не найден"


async def test_invalid_query_returns_problem_details_422_with_errors(client: AsyncClient) -> None:
    response = await client.get("/api/v1/officials", params={"limit": 101})

    assert response.status_code == 422
    body = response.json()
    assert body["title"] == "RequestValidationError"
    assert body["errors"][0]["loc"] == ["query", "limit"]


async def test_empty_database_gives_empty_lists(client: AsyncClient) -> None:
    officials = (await client.get("/api/v1/officials")).json()
    organs = (await client.get("/api/v1/organs")).json()

    assert officials == {"items": [], "total": 0}
    assert organs == {"items": [], "total": 0}
