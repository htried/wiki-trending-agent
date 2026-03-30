from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from wiki_trending_agent.config import settings
from wiki_trending_agent.integrations.serper_client import SerperClient
from wiki_trending_agent.integrations.wikimedia_client import \
    WikimediaStructuredContentClient
from wiki_trending_agent.wiki_structured import (compact_article_for_agent,
                                                 extract_section_text,
                                                 find_section_node_by_heading,
                                                 find_section_node_by_url,
                                                 first_article,
                                                 validate_sections_to_update)
from wiki_trending_agent.wikipedia_urls import article_url_from_project

AGENT_OUTPUT_INSTRUCTIONS = """
Your final message MUST be a single JSON object (no markdown fences) with these keys:

- wikipedia_article_url: Canonical URL to the article (https://{lang}.wikipedia.org/wiki/Title_with_underscores).
- summary: 2–4 short paragraphs in Markdown (bold/italics allowed). Cite like Wikipedia: at the end of each sentence
  that states a non-obvious or news-derived fact, add a numeric marker with square brackets, e.g. "… announced the deal.[1]"
  or "… according to early reports.[2] [3]". Use one marker per sentence when that sentence needs support; combine markers
  when one sentence rests on multiple sources (keep each number in its own brackets so they do not run together). Do NOT use markdown inline links [label](url) in summary — no bare URLs in
  the prose. Obvious or purely contextual sentences may omit a marker.
- whats_new: Same citation style as summary (sentence-level [n] markers, no markdown links in prose). Focus on what is
  newly relevant or not yet reflected in the article; contrast with fetch_wiki_content. Before claiming breaking news is
  absent, call fetch_wiki_section_content for the lede and plausible sections and compare to your news claims.
  If traffic is plausibly from unrelated uses of the same name, explain that clearly and state that no on-wiki update to
  reflect those stories is appropriate for this article—do not frame random same-name news as "what's new" for the topic.
- sections_to_update: Array of objects {"section_heading": "...", "section_url": "..."} copied EXACTLY from
  the fetch_wiki_content tool result field "section_index" (same strings as "heading" and "url" there).
  Do not invent anchors or headings; if unsure, omit the section.
  If the trend is driven by name ambiguity (homonyms, places, brands, or other topics that merely share a word with
  the article title but are NOT about this article's subject)—
  you MUST set sections_to_update to []: do not propose section edits to shoehorn unrelated current events into the article.
- suggested_update: Concrete, neutral, encyclopedic proposed wording (paragraph or bullets) using the SAME [n] style for
  any factual sentence that needs a source; no markdown inline links in the prose.
  If there is no RS-backed, on-topic development for this article's subject, set suggested_update to "" (empty string).
  Never suggest wording that adds unrelated local news, geography, or tangential "trending" topics that WP:NOTNEWS or
  undue weight would disallow for this subject.
- citations: Ordered list of sources matching the numbers used in summary, whats_new, and suggested_update: the first item
  is reference [1], the second is [2], etc. Each object: {"title": "Source name or headline", "url": "https://...", "reliability_note": "optional"}.
  Every number used in the prose must have a corresponding entry (reuse the same number when the same source supports
  multiple sentences). Only include sources that would plausibly meet English Wikipedia reliable-sources expectations (WP:RS):
  prefer wire services and broadsheets with editorial oversight (e.g. Reuters, AP, BBC, NYT, WSJ, major national dailies),
  official or academic publications where appropriate; exclude tabloid gossip, unverified blogs, and self-published
  sources unless the article is about that source. If you only have weak sources, include fewer citations, explain in
  reliability_note, and lower confidence.
- confidence: Number 0–1.
- event_candidate: Short label for a driving real-world event, or "" if unclear.

Also include "reason" set to the same text as "summary" for backward compatibility.
"""

SOURCE_GUIDELINES = (
    "When choosing what to cite and how to weight search_news hits, follow English Wikipedia WP:RS norms: "
    "favor established news organizations and official bodies; treat tabloids and partisan blogs as generally "
    "unreliable for factual claims unless the story is specifically about them. Prefer sources already present "
    "in Serper results that look like major outlets; second-pass search with a narrower query if needed. "
    "In prose, cite with [1], [2], … only; put URLs solely in the citations array in matching order. "
    "When hits concern a different topic that only shares the name, cite them only to support claims about "
    "confusion or traffic drivers—not as reasons to change the article body."
)


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
                    "description": (
                        "Search recent news for a query. Results vary in reliability; prefer items from recognized "
                        "news organizations when synthesizing facts for Wikipedia."
                    ),
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
                    "description": (
                        "Fetch Wikimedia Enterprise structured article JSON. Returns article_name, article_url, "
                        "abstract, description, and section_index: a flat list of {heading, url} for every section "
                        "in the article tree. Use section_index verbatim for sections_to_update."
                    ),
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
            {
                "type": "function",
                "function": {
                    "name": "fetch_wiki_section_content",
                    "description": (
                        "After fetch_wiki_content, load the full text body of one section by heading (and "
                        "optionally section_url from section_index) for the same project/page_title. Use this "
                        "to verify whether news claims are already stated in that section before writing whats_new."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "page_title": {"type": "string"},
                            "section_heading": {
                                "type": "string",
                                "description": "Section title as in fetch_wiki_content section_index.heading",
                            },
                            "section_url": {
                                "type": "string",
                                "description": "Optional exact section url from section_index to disambiguate",
                            },
                        },
                        "required": ["section_heading"],
                    },
                },
            },
        ]

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are an investigative trend-analysis agent for Wikipedia editors. "
                    "Use tools to gather external news and on-wiki structured content before answering. "
                    "If confidence is low, run a second, narrower search_news query. "
                    "If news is mostly about a different sense of the title (place, homonym, unrelated entity), say so and "
                    "omit editorial suggestions: empty sections_to_update, empty suggested_update, moderate confidence. "
                    "Focus on concrete, novel external events that are reported and may be driving trends for THIS subject, "
                    "not general or same-name news. "
                    + SOURCE_GUIDELINES
                    + " "
                    + AGENT_OUTPUT_INSTRUCTIONS
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyze why '{page_title}' is trending around {hour.isoformat()}. "
                    "Use tool calls first (news + wiki structured content). "
                    "Then output the JSON described in your instructions."
                ),
            },
        ]

        for _ in range(8):
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
                    "summary": content,
                    "confidence": 0.4,
                    "citations": [],
                    "event_candidate": "",
                    "whats_new": "",
                    "sections_to_update": [],
                    "suggested_update": "",
                }

        return {
            "reason": "Unable to determine confidently with available evidence.",
            "summary": "Unable to determine confidently with available evidence.",
            "confidence": 0.2,
            "citations": [],
            "event_candidate": "Potential unresolved news-driven trend",
            "whats_new": "",
            "sections_to_update": [],
            "suggested_update": "",
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
) -> tuple[Any, str | None]:
    """
    Returns (payload, error_message). On failure payload is often {} and error_message explains why.
    """
    if wikimedia_client is None:
        return {}, "wikimedia_enterprise_not_configured"
    try:
        return wikimedia_client.fetch_structured_content(project=project, page_title=page_title), None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def normalize_agent_result(
    project: str,
    page_title: str,
    result: dict[str, Any],
    known_sections: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    out = dict(result)
    default_url = article_url_from_project(project, page_title)
    out["wikipedia_article_url"] = str(out.get("wikipedia_article_url") or default_url)

    summary = out.get("summary")
    reason = out.get("reason")
    if summary and not reason:
        out["reason"] = str(summary)
    elif reason and not summary:
        out["summary"] = str(reason)
    elif not summary and not reason:
        out["reason"] = ""
        out["summary"] = ""

    raw_citations = out.get("citations", [])
    normalized_citations: list[dict[str, str]] = []
    if isinstance(raw_citations, list):
        for c in raw_citations:
            if isinstance(c, str):
                normalized_citations.append({"title": c, "url": c})
            elif isinstance(c, dict):
                url = str(c.get("url", "")).strip()
                if url:
                    entry: dict[str, str] = {
                        "title": str(c.get("title", url)).strip() or url,
                        "url": url,
                    }
                    note = str(c.get("reliability_note", "")).strip()
                    if note:
                        entry["reliability_note"] = note
                    normalized_citations.append(entry)
    out["citations"] = normalized_citations

    proposed: list[dict[str, Any]] = []
    raw_sections = out.get("sections_to_update")
    if isinstance(raw_sections, list):
        for s in raw_sections:
            if isinstance(s, dict):
                proposed.append(
                    {
                        "section_heading": str(
                            s.get("section_heading") or s.get("heading", ""),
                        ).strip(),
                        "section_url": str(s.get("section_url") or s.get("url", "")).strip(),
                    },
                )

    out["sections_skipped_not_in_article"] = []
    base = out["wikipedia_article_url"]
    if known_sections:
        verified, skipped = validate_sections_to_update(proposed, known_sections)
        out["sections_to_update"] = verified
        out["sections_skipped_not_in_article"] = skipped
        if skipped:
            sys_note = (
                f"\n\n_(System: {len(skipped)} proposed section(s) were not found in the Enterprise "
                "`section_index` and were removed—copy heading and url exactly from fetch_wiki_content.)_"
            )
            out["whats_new"] = str(out.get("whats_new", "")).strip() + sys_note
    else:
        sections = []
        for s in proposed:
            heading = str(s.get("section_heading", "")).strip()
            surl = str(s.get("section_url", "")).strip()
            if surl:
                sections.append({"section_heading": heading or surl.split("#")[-1], "section_url": surl})
            elif heading:
                frag = heading.replace(" ", "_")
                sections.append({"section_heading": heading, "section_url": f"{base}#{frag}"})
        out["sections_to_update"] = sections

    for key in ("whats_new", "suggested_update"):
        val = out.get(key)
        out[key] = str(val).strip() if val is not None else ""

    if not isinstance(out.get("event_candidate"), str):
        out["event_candidate"] = str(out.get("event_candidate", "") or "")

    return out


def analyze_page_with_agent(
    page_title: str,
    hour: datetime,
    emit: Callable[[str, dict], None],
    serper_client: SerperClient | None,
    wikimedia_client: WikimediaStructuredContentClient | None,
    wiki_project: str = "en.wikipedia",
    adapter: AgentAdapter | None = None,
) -> dict[str, Any]:
    known_sections: list[dict[str, str]] = []
    seen_section_keys: set[str] = set()
    last_wiki_cache: dict[str, Any] = {}

    def _remember_sections(rows: list[dict[str, str]]) -> None:
        for row in rows:
            key = (row.get("url") or "").strip() or _norm_heading_key(row.get("heading", ""))
            if not key or key in seen_section_keys:
                continue
            seen_section_keys.add(key)
            known_sections.append(dict(row))

    def _norm_heading_key(h: str) -> str:
        return " ".join(h.casefold().split())

    def search_news(args: dict) -> dict:
        payload = {"query": args.get("query", page_title), "time_window": args.get("time_window", "24h")}
        emit("AGENT_TOOL_CALL", {"tool": "search_news", "args": payload})
        result = _safe_news_search(serper_client, payload["query"], payload["time_window"])
        emit("AGENT_TOOL_RESULT", {"tool": "search_news", "result_count": len(result.get("news", []))})
        return result

    def fetch_wiki_content(args: dict) -> dict:
        payload = {
            "project": args.get("project", wiki_project),
            "page_title": args.get("page_title", page_title),
        }
        emit("AGENT_TOOL_CALL", {"tool": "fetch_wiki_content", "args": payload})
        raw, fetch_err = _safe_wiki_fetch(wikimedia_client, payload["project"], payload["page_title"])
        last_wiki_cache["raw"] = raw
        last_wiki_cache["project"] = payload["project"]
        last_wiki_cache["page_title"] = payload["page_title"]
        compact = compact_article_for_agent(raw)
        idx = compact.get("section_index")
        if isinstance(idx, list):
            rows = [r for r in idx if isinstance(r, dict) and str(r.get("heading", "")).strip()]
            _remember_sections([{"heading": str(r.get("heading", "")), "url": str(r.get("url", ""))} for r in rows])
        tool_payload: dict[str, Any] = {
            "tool": "fetch_wiki_content",
            "has_content": bool(compact.get("ok")),
            "section_count": compact.get("section_count", 0),
        }
        if fetch_err:
            tool_payload["fetch_error"] = fetch_err
        if not compact.get("ok"):
            err = compact.get("error")
            if err:
                tool_payload["parse_error"] = err
            hint = compact.get("hint")
            if hint:
                tool_payload["hint"] = hint
        emit("AGENT_TOOL_RESULT", tool_payload)
        return compact

    def fetch_wiki_section_content(args: dict) -> dict:
        payload = {
            "project": args.get("project", wiki_project),
            "page_title": args.get("page_title", page_title),
            "section_heading": str(args.get("section_heading", "")).strip(),
            "section_url": str(args.get("section_url", "")).strip(),
        }
        emit("AGENT_TOOL_CALL", {"tool": "fetch_wiki_section_content", "args": payload})
        cached_raw = last_wiki_cache.get("raw")
        if (
            cached_raw is None
            or last_wiki_cache.get("project") != payload["project"]
            or last_wiki_cache.get("page_title") != payload["page_title"]
        ):
            out = {
                "ok": False,
                "error": "call_fetch_wiki_content_first",
                "hint": "Run fetch_wiki_content for the same project and page_title before loading a section body.",
            }
            emit(
                "AGENT_TOOL_RESULT",
                {
                    "tool": "fetch_wiki_section_content",
                    "ok": False,
                    "error": out["error"],
                    "hint": out.get("hint"),
                },
            )
            return out
        if not payload["section_heading"] and not payload["section_url"]:
            out = {
                "ok": False,
                "error": "missing_section_heading_or_url",
                "hint": "Provide section_heading (and optionally section_url) from section_index.",
            }
            emit(
                "AGENT_TOOL_RESULT",
                {
                    "tool": "fetch_wiki_section_content",
                    "ok": False,
                    "error": out["error"],
                    "hint": out.get("hint"),
                },
            )
            return out
        art = first_article(cached_raw)
        if not art:
            out = {"ok": False, "error": "no_article_in_cache"}
            emit(
                "AGENT_TOOL_RESULT",
                {"tool": "fetch_wiki_section_content", "ok": False, "error": out["error"]},
            )
            return out
        node = None
        if payload["section_url"]:
            node = find_section_node_by_url(art, payload["section_url"])
        if node is None and payload["section_heading"]:
            node = find_section_node_by_heading(art, payload["section_heading"])
        if node is None:
            out = {
                "ok": False,
                "error": "section_not_found",
                "section_heading": payload["section_heading"],
                "section_url": payload["section_url"],
                "hint": "Copy heading and url exactly from fetch_wiki_content section_index.",
            }
            emit(
                "AGENT_TOOL_RESULT",
                {
                    "tool": "fetch_wiki_section_content",
                    "ok": False,
                    "error": out["error"],
                    "hint": out.get("hint"),
                },
            )
            return out
        text = extract_section_text(node)
        canon = (
            node.get("name")
            or node.get("headline")
            or node.get("title")
            or payload["section_heading"]
        )
        out = {
            "ok": True,
            "section_heading": str(canon),
            "section_url": str(node.get("url") or payload["section_url"] or ""),
            "text": text,
            "char_count": len(text),
        }
        emit(
            "AGENT_TOOL_RESULT",
            {
                "tool": "fetch_wiki_section_content",
                "ok": True,
                "char_count": out["char_count"],
            },
        )
        return out

    tools: dict[str, Callable[[dict], dict]] = {
        "search_news": search_news,
        "fetch_wiki_content": fetch_wiki_content,
        "fetch_wiki_section_content": fetch_wiki_section_content,
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
                tools["fetch_wiki_content"]({"project": wiki_project, "page_title": page_title})
                emit("AGENT_REASONING", {"mode": "fallback_no_openai_key"})
                url = article_url_from_project(wiki_project, page_title)
                msg = (
                    "Insufficient API credentials to run full LLM analysis; collected baseline evidence only. "
                    f"Article: {url}"
                )
                return {
                    "reason": msg,
                    "summary": msg,
                    "confidence": 0.2,
                    "citations": [],
                    "event_candidate": "Needs LLM-enabled rerun",
                    "wikipedia_article_url": url,
                    "whats_new": "",
                    "sections_to_update": [],
                    "suggested_update": "",
                }

        active_adapter = _FallbackAdapter()

    raw = active_adapter.run(page_title=page_title, hour=hour, tools=tools, emit=emit)
    return normalize_agent_result(wiki_project, page_title, raw, known_sections=known_sections)
