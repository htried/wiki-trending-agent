from collections.abc import Callable
from datetime import datetime

from wiki_trending_agent.services.agent_runtime import analyze_page_with_agent


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
            "reason": "Spike is likely linked to an active news cycle.",
            "confidence": 0.55,
            "citations": ["https://example.com/news"],
            "event_candidate": "Breaking story around the subject",
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
    )

    assert result["reason"]
    assert result["confidence"] == 0.55
    event_types = [event_type for event_type, _ in events]
    assert "AGENT_TOOL_CALL" in event_types
    assert "AGENT_TOOL_RESULT" in event_types
    assert "AGENT_REASONING" in event_types
