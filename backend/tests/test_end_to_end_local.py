from fastapi.testclient import TestClient

from wiki_trending_agent.main import app


def test_local_run_happy_path() -> None:
    client = TestClient(app)

    create = client.post("/runs", json={"hour": "2026-03-29T12:00:00"})
    assert create.status_code == 201

    run_id = create.json()["run_id"]
    detail = client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["run_id"] == run_id
