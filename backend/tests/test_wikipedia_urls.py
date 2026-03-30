from wiki_trending_agent.wikipedia_urls import article_url_from_project


def test_article_url_en_wikipedia() -> None:
    url = article_url_from_project("en.wikipedia", "Palm_Sunday")
    assert url == "https://en.wikipedia.org/wiki/Palm_Sunday"
