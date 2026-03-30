"""Parse Wikimedia Enterprise structured-contents JSON for agent consumption."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlparse


def _looks_like_article_dict(d: dict[str, Any]) -> bool:
    """Heuristic: Enterprise / JSON-LD articles vary by endpoint version."""
    if not d:
        return False
    if any(
        k in d
        for k in (
            "sections",
            "name",
            "abstract",
            "headline",
            "has_parts",
            "has_part",
            "article_body",
            "articleBody",
        )
    ):
        return True
    url = str(d.get("url") or "")
    title = d.get("title")
    if isinstance(title, str) and title.strip() and "wikipedia.org/wiki/" in url:
        return True
    if d.get("identifier") is not None and ("wikipedia.org" in url or "/wiki/" in url):
        return True
    return False


def first_article(payload: Any) -> dict[str, Any] | None:
    """Enterprise API may return a list of article objects or a single object."""
    if payload is None:
        return None
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and _looks_like_article_dict(item):
                return item
        for item in payload:
            if isinstance(item, dict):
                return item
        return None
    if isinstance(payload, dict):
        if _looks_like_article_dict(payload):
            return payload
        graph = payload.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and _looks_like_article_dict(item):
                    return item
    return None


def _walk_section_nodes(node: Any, out: list[dict[str, str]], depth: int) -> None:
    if depth > 64:
        return
    if isinstance(node, dict):
        name = node.get("name") or node.get("headline") or node.get("title")
        url = node.get("url")
        if name is not None and str(name).strip():
            out.append({"heading": str(name).strip(), "url": str(url).strip() if url else ""})
        for key in (
            "sections",
            "has_part",
            "has_parts",
            "subitems",
            "parts",
            "article_section",
        ):
            child = node.get(key)
            if isinstance(child, list):
                for item in child:
                    _walk_section_nodes(item, out, depth + 1)
            elif isinstance(child, dict):
                _walk_section_nodes(child, out, depth + 1)
    elif isinstance(node, list):
        for item in node:
            _walk_section_nodes(item, out, depth)


def extract_section_index(article: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten Enterprise `sections` / `has_parts` tree into {heading, url} rows (deduped by url then heading)."""
    out: list[dict[str, str]] = []
    raw_sections = article.get("sections")
    if isinstance(raw_sections, list):
        for item in raw_sections:
            _walk_section_nodes(item, out, 0)
    elif isinstance(raw_sections, dict):
        _walk_section_nodes(raw_sections, out, 0)

    for key in ("has_parts", "has_part"):
        hp = article.get(key)
        if isinstance(hp, list):
            for item in hp:
                _walk_section_nodes(item, out, 0)
        elif isinstance(hp, dict):
            _walk_section_nodes(hp, out, 0)

    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in out:
        key = row["url"] or row["heading"].casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def compact_article_for_agent(
    raw_response: Any,
    abstract_max_chars: int = 2800,
    description_max_chars: int = 800,
) -> dict[str, Any]:
    """
    Build a small JSON-safe dict for the LLM tool result.
    Omits heavy fields (infoboxes, full tables, editor metadata).
    """
    article = first_article(raw_response)
    if not article:
        return {
            "ok": False,
            "error": "empty_or_unrecognized_payload",
            "section_index": [],
            "hint": "Response was not a recognizable Enterprise article object.",
        }

    abstract = str(article.get("abstract") or "")
    if len(abstract) > abstract_max_chars:
        abstract = abstract[:abstract_max_chars] + "…"

    description = str(article.get("description") or "")
    if len(description) > description_max_chars:
        description = description[:description_max_chars] + "…"

    section_index = extract_section_index(article)

    return {
        "ok": True,
        "article_name": str(article.get("name") or ""),
        "article_url": str(article.get("url") or ""),
        "abstract": abstract,
        "description": description,
        "section_index": section_index,
        "section_count": len(section_index),
        "instruction": (
            "For sections_to_update, copy each section_heading and section_url EXACTLY from section_index "
            "(same spelling and full URL including fragment). Do not invent section names or anchors."
        ),
    }


def _norm_heading(s: str) -> str:
    return " ".join(s.casefold().split())


def _fragment(url: str) -> str:
    try:
        return unquote(urlparse(url).fragment or "").replace("_", " ").casefold()
    except Exception:
        return ""


def match_known_section(
    proposed_heading: str,
    proposed_url: str,
    known: list[dict[str, str]],
) -> dict[str, str] | None:
    """Return the canonical section_index row if proposed matches url and/or heading."""
    ph = _norm_heading(proposed_heading)
    pu = (proposed_url or "").strip()
    pf = _fragment(pu)

    best: dict[str, str] | None = None
    for row in known:
        kh = _norm_heading(row.get("heading", ""))
        ku = (row.get("url") or "").strip()
        kf = _fragment(ku)

        if pu and ku and pu == ku:
            return row
        if pu and ku:
            # Same path + fragment (normalized)
            a, b = urlparse(pu), urlparse(ku)
            if a.path == b.path and pf and kf and pf == kf:
                return row
        if ph and kh and ph == kh:
            best = row
    return best


def validate_sections_to_update(
    proposed: list[dict[str, Any]],
    known: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Keep only sections that exist in Enterprise section_index (by URL or heading).
    Returns (verified_sections, skipped_with_reason).
    """
    verified: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for item in proposed:
        if not isinstance(item, dict):
            continue
        heading = str(item.get("section_heading", "")).strip()
        surl = str(item.get("section_url", "")).strip()
        if not heading and not surl:
            continue

        match = match_known_section(heading, surl, known)
        if match:
            verified.append(
                {
                    "section_heading": match.get("heading", heading),
                    "section_url": match.get("url") or surl,
                },
            )
        else:
            skipped.append(
                {
                    "section_heading": heading,
                    "section_url": surl,
                    "reason": "not_found_in_enterprise_section_index",
                },
            )

    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for row in verified:
        key = row["section_url"] or _norm_heading(row["section_heading"])
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(row)

    return uniq, skipped


def find_section_node_by_heading(
    article: dict[str, Any],
    heading: str,
) -> dict[str, Any] | None:
    """Return the first section dict whose name/headline/title matches (normalized whitespace/case)."""
    target = _norm_heading(heading)
    if not target:
        return None

    def walk(node: Any, depth: int) -> dict[str, Any] | None:
        if depth > 64:
            return None
        if isinstance(node, dict):
            name = node.get("name") or node.get("headline") or node.get("title")
            if name is not None and _norm_heading(str(name)) == target:
                return node
            for key in (
                "sections",
                "has_part",
                "has_parts",
                "subitems",
                "parts",
                "article_section",
            ):
                child = node.get(key)
                if isinstance(child, list):
                    for item in child:
                        hit = walk(item, depth + 1)
                        if hit is not None:
                            return hit
                elif isinstance(child, dict):
                    hit = walk(child, depth + 1)
                    if hit is not None:
                        return hit
        elif isinstance(node, list):
            for item in node:
                hit = walk(item, depth + 1)
                if hit is not None:
                    return hit
        return None

    return walk(article, 0)


def _urls_equivalent(a: str, b: str) -> bool:
    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return False
    if a == b:
        return True
    try:
        pa, pb = urlparse(a), urlparse(b)
        if pa.path != pb.path:
            return False
        fa, fb = unquote(pa.fragment or ""), unquote(pb.fragment or "")
        return bool(fa and fb and fa.replace("_", " ").casefold() == fb.replace("_", " ").casefold())
    except Exception:
        return False


def find_section_node_by_url(article: dict[str, Any], section_url: str) -> dict[str, Any] | None:
    """Return the first section dict whose url matches section_url (exact or same path+fragment)."""
    want = (section_url or "").strip()
    if not want:
        return None

    def walk(node: Any, depth: int) -> dict[str, Any] | None:
        if depth > 64:
            return None
        if isinstance(node, dict):
            u = node.get("url")
            if isinstance(u, str) and _urls_equivalent(u, want):
                return node
            for key in (
                "sections",
                "has_part",
                "has_parts",
                "subitems",
                "parts",
                "article_section",
            ):
                child = node.get(key)
                if isinstance(child, list):
                    for item in child:
                        hit = walk(item, depth + 1)
                        if hit is not None:
                            return hit
                elif isinstance(child, dict):
                    hit = walk(child, depth + 1)
                    if hit is not None:
                        return hit
        elif isinstance(node, list):
            for item in node:
                hit = walk(item, depth + 1)
                if hit is not None:
                    return hit
        return None

    return walk(article, 0)


def extract_section_text(section: dict[str, Any], max_chars: int = 16000) -> str:
    """
    Pull human-readable text from an Enterprise section subtree.
    Collects string fields like articleBody/text/content and text inside has_part-style lists,
    but does not descend into nested `sections` (those are separate headings).
    """
    chunks: list[str] = []

    def add(s: str) -> None:
        t = s.strip()
        if t and t not in chunks:
            chunks.append(t)

    def walk_content(o: Any, depth: int) -> None:
        if depth > 48:
            return
        if isinstance(o, str):
            if len(o.strip()) > 2:
                add(o)
        elif isinstance(o, dict):
            for key in ("articleBody", "abstract", "description", "text", "content", "value", "html"):
                v = o.get(key)
                if isinstance(v, str) and v.strip():
                    add(v)
            for key in ("has_part", "has_parts", "article_section", "parts", "subitems"):
                child = o.get(key)
                if isinstance(child, list):
                    for item in child:
                        walk_content(item, depth + 1)
                elif isinstance(child, dict):
                    walk_content(child, depth + 1)
        elif isinstance(o, list):
            for item in o:
                walk_content(item, depth + 1)

    walk_content(section, 0)
    joined = "\n\n".join(chunks)
    if len(joined) > max_chars:
        joined = joined[:max_chars] + "…"
    return joined
