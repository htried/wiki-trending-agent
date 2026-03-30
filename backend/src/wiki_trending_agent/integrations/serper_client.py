from __future__ import annotations

import httpx


class SerperClient:
    def __init__(self, api_key: str, base_url: str = "https://google.serper.dev", timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def build_query_payload(self, query: str, time_window: str) -> dict[str, str]:
        return {"q": query, "time": time_window}

    def search_news(self, query: str, time_window: str = "24h") -> dict:
        payload = self.build_query_payload(query, time_window)
        response = httpx.post(
            f"{self._base_url}/news",
            headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()
