from fastapi.testclient import TestClient

from wiki_trending_agent.main import app


def test_create_run_returns_run_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/runs",
        json={"hour": "2026-03-29T12:00:00", "top_k_pages": 3},
    )

    assert response.status_code == 201
    data = response.json()
    assert "run_id" in data
    assert data["top_k_pages"] == 3
