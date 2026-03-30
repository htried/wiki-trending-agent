from __future__ import annotations

from urllib.parse import quote

import httpx

# On-demand URL shape (not /{project}/structured-contents/...):
# https://enterprise.wikimedia.com/docs/on-demand/#article-structured-contents-beta


def _filters_for_wiki_project(project: str) -> list[dict[str, str]]:
    """
    Map settings like en.wikipedia to Enterprise metadata filters.
    POST body uses the same filter objects as in the official examples.
    """
    p = (project or "en.wikipedia").strip().lower()
    if not p:
        return [{"field": "in_language.identifier", "value": "en"}]
    if "." in p:
        lang, _rest = p.split(".", 1)
        if lang:
            return [{"field": "in_language.identifier", "value": lang}]
    return [{"field": "in_language.identifier", "value": "en"}]


class WikimediaStructuredContentClient:
    """Wikimedia Enterprise On-demand API with auth per https://enterprise.wikimedia.com/docs/authentication/#login"""

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://api.enterprise.wikimedia.com/v2",
        auth_url: str = "https://auth.enterprise.wikimedia.com/v1",
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._auth_url = auth_url.rstrip("/")
        self._timeout = timeout
        self._access_token: str | None = None
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> WikimediaStructuredContentClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _login(self) -> None:
        response = self._client.post(
            f"{self._auth_url}/login",
            json={"username": self._username, "password": self._password},
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(
                "Wikimedia Enterprise login succeeded but no access_token in response",
            )
        self._access_token = token

    def fetch_structured_content(self, project: str, page_title: str) -> dict | list:
        if not self._access_token:
            self._login()

        title_path = quote(page_title, safe="()%!'._~-")
        url = f"{self._base_url}/structured-contents/{title_path}"
        body = {
            "filters": _filters_for_wiki_project(project),
            "limit": 5,
        }
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        response = self._client.post(url, headers=headers, json=body)

        if response.status_code == 401:
            self._login()
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = self._client.post(url, headers=headers, json=body)

        response.raise_for_status()
        return response.json()
