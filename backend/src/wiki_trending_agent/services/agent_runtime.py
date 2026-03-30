from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from wiki_trending_agent.config import settings
from wiki_trending_agent.integrations.serper_client import SerperClient
from wiki_trending_agent.integrations.wikimedia_client import WikimediaStructuredContentClient


class AgentAdapter(Protocol):
    def run(
        self,
        page_title: str,
        hour: datetime,
        tools: dict[str, Callable[[dict], dict]],
        emit: Callable[[str, dict], None],
    ) -> dict:
        ...


class OpenAIAgentAdapter:
    """Tool-calling agent loop backed by OpenAI Chat Completions."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def run(
        self,
        page_title: str,
        hour: datetime,
        tools: dict[str, Callable[[dict], dict]],
        emit: Callable[[str, dict], None],
    ) -> dict:
        tool_specs = [
            {
                "type": "function",
                "function": {
                    "name": "search_news",
                    "description": "Search recent news for a query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "time_window": {"type": "string"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_wiki_content",
                    "description": "Fetch Wikimedia structured article content for a page title.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "page_title": {"type": "string"},
                        },
                        "required": ["project", "page_title"],
                    },
                },
            },
        ]

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are an investigative trend-analysis agent. Use tools to gather evidence, "
                    "perform second-pass search when confidence is low, and output JSON with keys: "
                    "reason, confidence, citations, event_candidate."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyze why '{page_title}' is trending around {hour.isoformat()}. "
                    "Use tool calls before final answer."
                ),
            },
        ]

        for _ in range(6):
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tool_specs,
                tool_choice="auto",
            )
            message = completion.choices[0].message

            if message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments,
                                },
                            }
                            for call in message.tool_calls
                        ],
                    }
                )
                for tool_call in message.tool_calls:
                    args = json.loads(tool_call.function.arguments or "{}")
                    tool_result = tools[tool_call.function.name](args)
                    emit("AGENT_REASONING", {"tool_name": tool_call.function.name})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result),
                        }
                    )
                continue

            content = message.content or "{}"
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "reason": content,
                    "confidence": 0.4,
                    "citations": [],
                    "event_candidate": "",
                }

        return {
            "reason": "Unable to determine confidently with available evidence.",
            "confidence": 0.2,
            "citations": [],
            "event_candidate": "Potential unresolved news-driven trend",
        }


def _safe_news_search(serper_client: SerperClient | None, query: str, time_window: str) -> dict:
    if serper_client is None:
        return {"news": []}
    try:
        return serper_client.search_news(query=query, time_window=time_window)
    except Exception:
        return {"news": []}


def _safe_wiki_fetch(
    wikimedia_client: WikimediaStructuredContentClient | None,
    project: str,
    page_title: str,
) -> dict:
    if wikimedia_client is None:
        return {"content": {}}
    try:
        return wikimedia_client.fetch_structured_content(project=project, page_title=page_title)
    except Exception:
        return {"content": {}}


def analyze_page_with_agent(
    page_title: str,
    hour: datetime,
    emit: Callable[[str, dict], None],
    serper_client: SerperClient | None,
    wikimedia_client: WikimediaStructuredContentClient | None,
    adapter: AgentAdapter | None = None,
) -> dict[str, Any]:
    def search_news(args: dict) -> dict:
        payload = {"query": args.get("query", page_title), "time_window": args.get("time_window", "24h")}
        emit("AGENT_TOOL_CALL", {"tool": "search_news", "args": payload})
        result = _safe_news_search(serper_client, payload["query"], payload["time_window"])
        emit("AGENT_TOOL_RESULT", {"tool": "search_news", "result_count": len(result.get("news", []))})
        return result

    def fetch_wiki_content(args: dict) -> dict:
        payload = {
            "project": args.get("project", "en.wikipedia"),
            "page_title": args.get("page_title", page_title),
        }
        emit("AGENT_TOOL_CALL", {"tool": "fetch_wiki_content", "args": payload})
        result = _safe_wiki_fetch(wikimedia_client, payload["project"], payload["page_title"])
        emit("AGENT_TOOL_RESULT", {"tool": "fetch_wiki_content", "has_content": bool(result)})
        return result

    tools: dict[str, Callable[[dict], dict]] = {
        "search_news": search_news,
        "fetch_wiki_content": fetch_wiki_content,
    }

    active_adapter: AgentAdapter
    if adapter is not None:
        active_adapter = adapter
    elif settings.openai_api_key:
        active_adapter = OpenAIAgentAdapter(settings.openai_api_key, settings.openai_model)
    else:
        class _FallbackAdapter:
            def run(
                self,
                page_title: str,
                hour: datetime,
                tools: dict[str, Callable[[dict], dict]],
                emit: Callable[[str, dict], None],
            ) -> dict:
                tools["search_news"]({"query": page_title, "time_window": "24h"})
                tools["fetch_wiki_content"]({"project": "en.wikipedia", "page_title": page_title})
                emit("AGENT_REASONING", {"mode": "fallback_no_openai_key"})
                return {
                    "reason": "Insufficient API credentials to run full LLM analysis; collected baseline evidence.",
                    "confidence": 0.2,
                    "citations": [],
                    "event_candidate": "Needs LLM-enabled rerun",
                }

        active_adapter = _FallbackAdapter()

    return active_adapter.run(page_title=page_title, hour=hour, tools=tools, emit=emit)
