from wiki_trending_agent.wiki_structured import (
    compact_article_for_agent,
    extract_section_index,
    extract_section_text,
    find_section_node_by_heading,
    find_section_node_by_url,
    first_article,
    validate_sections_to_update,
)


def test_first_article_from_list() -> None:
    payload = [{"name": "Foo", "abstract": "x", "sections": []}]
    art = first_article(payload)
    assert art is not None
    assert art["name"] == "Foo"


def test_first_article_accepts_has_parts_without_sections() -> None:
    payload = {
        "name": "Gary_Woodland",
        "url": "https://en.wikipedia.org/wiki/Gary_Woodland",
        "identifier": 123,
        "has_parts": [
            {
                "name": "Career",
                "url": "https://en.wikipedia.org/wiki/Gary_Woodland#Career",
                "text": "Professional highlights.",
            },
        ],
    }
    art = first_article(payload)
    assert art is not None
    assert art["name"] == "Gary_Woodland"
    idx = extract_section_index(art)
    assert any(r["heading"] == "Career" for r in idx)


def test_extract_section_index_nested() -> None:
    article = {
        "name": "Test",
        "url": "https://en.wikipedia.org/wiki/Test",
        "sections": [
            {
                "name": "History",
                "url": "https://en.wikipedia.org/wiki/Test#History",
                "sections": [
                    {
                        "name": "Early years",
                        "url": "https://en.wikipedia.org/wiki/Test#Early_years",
                    },
                ],
            },
        ],
    }
    idx = extract_section_index(article)
    headings = {r["heading"] for r in idx}
    assert "History" in headings
    assert "Early years" in headings
    assert any("Early_years" in r["url"] for r in idx)


def test_compact_article_for_agent() -> None:
    raw = [
        {
            "name": "Palm_Sunday",
            "url": "https://en.wikipedia.org/wiki/Palm_Sunday",
            "abstract": "A" * 100,
            "description": "Short",
            "sections": [
                {"name": "Observance", "url": "https://en.wikipedia.org/wiki/Palm_Sunday#Observance"},
            ],
        },
    ]
    compact = compact_article_for_agent(raw)
    assert compact["ok"] is True
    assert compact["section_count"] == 1
    assert compact["section_index"][0]["heading"] == "Observance"


def test_validate_sections_keeps_exact_url() -> None:
    known = [
        {"heading": "History", "url": "https://en.wikipedia.org/wiki/Foo#History"},
    ]
    proposed = [
        {"section_heading": "History", "section_url": "https://en.wikipedia.org/wiki/Foo#History"},
    ]
    verified, skipped = validate_sections_to_update(proposed, known)
    assert len(verified) == 1
    assert not skipped


def test_validate_sections_drops_unknown() -> None:
    known = [{"heading": "History", "url": "https://en.wikipedia.org/wiki/Foo#History"}]
    proposed = [{"section_heading": "Fake", "section_url": "https://en.wikipedia.org/wiki/Foo#Fake"}]
    verified, skipped = validate_sections_to_update(proposed, known)
    assert not verified
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "not_found_in_enterprise_section_index"


def test_validate_matches_heading_only() -> None:
    known = [{"heading": "In popular culture", "url": "https://en.wikipedia.org/wiki/Foo#In_popular_culture"}]
    proposed = [{"section_heading": "In popular culture", "section_url": ""}]
    verified, skipped = validate_sections_to_update(proposed, known)
    assert len(verified) == 1
    assert verified[0]["section_url"] == known[0]["url"]


def test_find_section_node_by_heading_and_extract_text() -> None:
    article = {
        "name": "Test",
        "sections": [
            {
                "name": "History",
                "url": "https://en.wikipedia.org/wiki/Test#History",
                "text": "The city was founded in 1900.",
                "sections": [
                    {
                        "name": "Modern era",
                        "articleBody": "Recent elections were held in March.",
                    },
                ],
            },
        ],
    }
    hist = find_section_node_by_heading(article, "history")
    assert hist is not None
    assert "1900" in extract_section_text(hist)
    modern = find_section_node_by_heading(article, "Modern era")
    assert modern is not None
    assert "March" in extract_section_text(modern)


def test_find_section_node_by_url() -> None:
    article = {
        "name": "Test",
        "sections": [
            {
                "name": "Reactions",
                "url": "https://en.wikipedia.org/wiki/Test#Reactions",
                "content": "Leaders condemned the attack.",
            },
        ],
    }
    node = find_section_node_by_url(
        article,
        "https://en.wikipedia.org/wiki/Test#Reactions",
    )
    assert node is not None
    assert "condemned" in extract_section_text(node)
