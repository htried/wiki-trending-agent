from fastapi.testclient import TestClient

from wiki_trending_agent.main import app


def test_run_stream_emits_started_event() -> None:
    client = TestClient(app)
    create_resp = client.post("/runs", json={"hour": "2026-03-29T12:00:00"})
    run_id = create_resp.json()["run_id"]

    response = client.get(f"/runs/{run_id}/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
