from __future__ import annotations

import httpx


class WikimediaStructuredContentClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.enterprise.wikimedia.com/v2",
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_structured_content(self, project: str, page_title: str) -> dict:
        url = f"{self._base_url}/{project}/structured-contents/{page_title}"
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()
