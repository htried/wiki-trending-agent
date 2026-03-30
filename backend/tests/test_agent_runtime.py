from collections.abc import Callable
from datetime import datetime
from typing import Any

from wiki_trending_agent.services.agent_runtime import analyze_page_with_agent


class StubWikimediaClient:
    """Returns a minimal Enterprise-shaped article for section-body tests."""

    def fetch_structured_content(self, project: str, page_title: str) -> Any:
        return [
            {
                "name": page_title.replace("_", " "),
                "url": f"https://en.wikipedia.org/wiki/{page_title}",
                "abstract": "Top-level abstract only.",
                "sections": [
                    {
                        "name": "Breaking",
                        "url": f"https://en.wikipedia.org/wiki/{page_title}#Breaking",
                        "text": "This paragraph already mentions the overnight arrest.",
                    },
                ],
            },
        ]


class FakeAdapterThatReadsSection:
    def run(
        self,
        page_title: str,
        hour: datetime,
        tools: dict[str, Callable[[dict], dict]],
        emit: Callable[[str, dict], None],
    ) -> dict:
        tools["fetch_wiki_content"]({"project": "en.wikipedia", "page_title": page_title})
        sec = tools["fetch_wiki_section_content"]({"section_heading": "Breaking"})
        assert sec.get("ok") is True
        assert "overnight arrest" in str(sec.get("text", ""))
        emit("AGENT_REASONING", {"step": "verified_section"})
        return {
            "reason": "News already in Breaking section.",
            "summary": "News already in Breaking section.",
            "confidence": 0.9,
            "citations": [],
            "event_candidate": "",
            "whats_new": "",
            "sections_to_update": [],
            "suggested_update": "",
        }


class FakeAdapter:
    def run(
        self,
        page_title: str,
        hour: datetime,
        tools: dict[str, Callable[[dict], dict]],
        emit: Callable[[str, dict], None],
    ) -> dict:
        tools["search_news"]({"query": page_title, "time_window": "24h"})
        tools["fetch_wiki_content"](
            {"project": "en.wikipedia", "page_title": page_title}
        )
        tools["search_news"](
            {"query": f"why is {page_title} trending", "time_window": "24h"}
        )
        emit("AGENT_REASONING", {"step": "synthesis"})
        return {
            "reason": "Spike is likely linked to an active news cycle.[1]",
            "summary": "Spike is likely linked to an active news cycle.[1]",
            "confidence": 0.55,
            "citations": [{"title": "Example", "url": "https://example.com/news"}],
            "event_candidate": "Breaking story around the subject",
            "whats_new": "Fresh coverage not yet in the article lede.",
            "sections_to_update": [{"section_heading": "Current events", "section_url": "https://en.wikipedia.org/wiki/Palm_Sunday#Current_events"}],
            "suggested_update": "Add one sentence in the lede citing the breaking source.",
        }


def test_agent_runtime_emits_tool_events_and_returns_reason() -> None:
    events: list[tuple[str, dict]] = []

    def emit(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    result = analyze_page_with_agent(
        page_title="Palm_Sunday",
        hour=datetime.fromisoformat("2026-03-29 12:00:00"),
        adapter=FakeAdapter(),
        emit=emit,
        serper_client=None,
        wikimedia_client=None,
        wiki_project="en.wikipedia",
    )

    assert result["reason"]
    assert "wikipedia.org/wiki/Palm_Sunday" in result["wikipedia_article_url"]
    assert result["confidence"] == 0.55
    assert result["citations"][0]["url"] == "https://example.com/news"
    event_types = [event_type for event_type, _ in events]
    assert "AGENT_TOOL_CALL" in event_types
    assert "AGENT_TOOL_RESULT" in event_types
    assert "AGENT_REASONING" in event_types


def test_fetch_wiki_section_content_tool_uses_cached_structured_payload() -> None:
    events: list[tuple[str, dict]] = []

    def emit(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    result = analyze_page_with_agent(
        page_title="Example_Page",
        hour=datetime.fromisoformat("2026-03-29 12:00:00"),
        adapter=FakeAdapterThatReadsSection(),
        emit=emit,
        serper_client=None,
        wikimedia_client=StubWikimediaClient(),
        wiki_project="en.wikipedia",
    )

    assert result["confidence"] == 0.9
    tool_calls = [p for t, p in events if t == "AGENT_TOOL_CALL" and p.get("tool")]
    tools_used = {p["tool"] for p in tool_calls}
    assert "fetch_wiki_content" in tools_used
    assert "fetch_wiki_section_content" in tools_used
