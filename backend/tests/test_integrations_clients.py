from wiki_trending_agent.integrations.serper_client import SerperClient


def test_serper_client_builds_time_limited_request() -> None:
    client = SerperClient(api_key="test")
    payload = client.build_query_payload("Palm Sunday", "24h")

    assert payload["q"] == "Palm Sunday"
    assert payload["time"] == "24h"
