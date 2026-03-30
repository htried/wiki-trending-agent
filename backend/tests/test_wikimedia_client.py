import json

import httpx

from wiki_trending_agent.integrations.wikimedia_client import WikimediaStructuredContentClient


def test_wikimedia_client_logs_in_then_fetches_structured_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            assert json.loads(request.content) == {
                "username": "testuser",
                "password": "secret",
            }
            return httpx.Response(
                200,
                json={
                    "access_token": "tok-123",
                    "id_token": "id-1",
                    "refresh_token": "ref-1",
                    "expires_in": 300,
                },
            )
        if "/structured-contents/Test_Page" in request.url.path:
            assert request.method == "POST"
            assert request.headers.get("authorization") == "Bearer tok-123"
            body = json.loads(request.content)
            assert body["filters"] == [{"field": "in_language.identifier", "value": "en"}]
            assert body.get("limit") == 5
            return httpx.Response(
                200,
                json=[{"name": "Test_Page", "sections": []}],
            )
        return httpx.Response(404, text="not found")

    transport = httpx.MockTransport(handler)
    client = WikimediaStructuredContentClient(
        username="testuser",
        password="secret",
        base_url="https://api.example/v2",
        auth_url="https://auth.example/v1",
        transport=transport,
    )
    try:
        data = client.fetch_structured_content("en.wikipedia", "Test_Page")
    finally:
        client.close()

    assert isinstance(data, list)
    assert data[0]["name"] == "Test_Page"
