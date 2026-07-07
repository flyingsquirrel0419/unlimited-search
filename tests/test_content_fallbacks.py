import json

from unlimited_search.engine.content_fallbacks import extract_metadata, try_content_fallbacks
from unlimited_search.engine.models import ResponseEnvelope, Verdict
from unlimited_search.engine.reader import UnlimitedSearchReader
from unlimited_search.engine.transport import TransportResult


class FakeTransport:
    def __init__(self, responses: dict[str, ResponseEnvelope | None]) -> None:
        self.responses = responses
        self.urls: list[str] = []

    def get(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        self.urls.append(url)
        response = self.responses.get(url)
        if response is None:
            return TransportResult(None, "no_fixture")
        return TransportResult(response)


def test_jina_json_content_fallback_succeeds() -> None:
    jina_url = "https://r.jina.ai/https://example.com/post"
    transport = FakeTransport(
        {
            jina_url: ResponseEnvelope(
                200,
                json.dumps(
                    {
                        "data": {
                            "title": "Example",
                            "url": "https://example.com/post",
                            "content": "This is a long markdown body. " * 8,
                        }
                    }
                ),
                jina_url,
                headers={"content-type": "application/json"},
            )
        }
    )

    result = try_content_fallbacks("https://example.com/post", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.route == "jina-json"
    assert result.content_type == "markdown"
    assert "long markdown body" in result.content


def test_jina_json_content_fallback_rejects_block_page_text() -> None:
    jina_url = "https://r.jina.ai/https://www.reddit.com/r/programming/.json"
    transport = FakeTransport(
        {
            jina_url: ResponseEnvelope(
                200,
                json.dumps(
                    {
                        "data": {
                            "title": "",
                            "url": "https://www.reddit.com/r/programming/.json",
                            "content": (
                                "You've been blocked by network security.\n\n"
                                "To continue, log in to your Reddit account or use your developer token.\n\n"
                                "File a ticket if this is a mistake."
                            ),
                        }
                    }
                ),
                jina_url,
                headers={"content-type": "application/json"},
            )
        }
    )

    result = try_content_fallbacks("https://www.reddit.com/r/programming/.json", transport)  # type: ignore[arg-type]

    assert result is None


def test_jina_alternate_feed_fallback_succeeds() -> None:
    jina_url = "https://r.jina.ai/https://example.com"
    feed_url = "https://example.com/feed.xml"
    transport = FakeTransport(
        {
            jina_url: ResponseEnvelope(
                200,
                json.dumps(
                    {
                        "data": {
                            "content": "",
                            "external": {
                                "alternate": [
                                    {"href": feed_url, "type": "application/rss+xml"},
                                ]
                            },
                        }
                    }
                ),
                jina_url,
                headers={"content-type": "application/json"},
            ),
            feed_url: ResponseEnvelope(
                200,
                "<rss><channel><title>Feed</title><item><title>One</title><link>https://example.com/1</link></item></channel></rss>",
                feed_url,
            ),
        }
    )

    result = try_content_fallbacks("https://example.com", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.route == "rss-discovery"
    assert result.metadata["exact_match"] is False
    assert result.metadata["recovery_scope"] == "site_feed"
    payload = json.loads(result.content)
    assert payload["feed"]["title"] == "Feed"
    assert payload["entries"][0]["title"] == "One"


def test_origin_feed_candidate_fallback_succeeds_without_jina_alternate() -> None:
    jina_url = "https://r.jina.ai/https://example.com/article"
    feed_url = "https://example.com/feed"
    transport = FakeTransport(
        {
            jina_url: ResponseEnvelope(200, json.dumps({"data": {"content": ""}}), jina_url),
            feed_url: ResponseEnvelope(
                200,
                "<feed><title>Atom</title><entry><title>Entry</title><link href='https://example.com/e'/></entry></feed>",
                feed_url,
            ),
        }
    )

    result = try_content_fallbacks("https://example.com/article", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.route == "rss-discovery"
    assert "https://example.com/feed" in transport.urls
    assert json.loads(result.content)["entries"][0]["link"] == "https://example.com/e"
    assert result.metadata["exact_match"] is False
    assert result.metadata["recovery_scope"] == "site_feed"


def test_rss_fallback_marks_exact_entry_match() -> None:
    url = "https://example.com/article"
    jina_url = "https://r.jina.ai/https://example.com/article"
    feed_url = "https://example.com/feed"
    transport = FakeTransport(
        {
            jina_url: ResponseEnvelope(200, json.dumps({"data": {"content": ""}}), jina_url),
            feed_url: ResponseEnvelope(
                200,
                "<rss><channel><title>Feed</title><item><title>Article</title><link>https://example.com/article/</link></item></channel></rss>",
                feed_url,
            ),
        }
    )

    result = try_content_fallbacks(url, transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.route == "rss-discovery"
    assert result.metadata["exact_match"] is True
    assert result.metadata["matched_entry_url"] == "https://example.com/article/"
    assert result.metadata["recovery_scope"] == "exact_page"


def test_metadata_salvage_extracts_ogp_and_json_ld() -> None:
    html = """
    <html><head>
      <title>Fallback Title</title>
      <meta property="og:title" content="OG Title">
      <meta name="description" content="Short description">
      <script type="application/ld+json">{"@type":"NewsArticle","headline":"Story"}</script>
    </head><body></body></html>
    """

    metadata = extract_metadata(html)

    assert metadata["meta"]["og:title"] == "OG Title"
    assert metadata["meta"]["description"] == "Short description"
    assert metadata["json_ld"][0]["headline"] == "Story"


def test_metadata_salvage_does_not_accept_challenge_title_only() -> None:
    url = "https://blocked.example"
    jina_url = "https://r.jina.ai/https://blocked.example"
    transport = FakeTransport(
        {
            jina_url: ResponseEnvelope(403, "blocked", jina_url),
            url: ResponseEnvelope(
                200,
                "<html><head><title>Attention Required! | Cloudflare</title></head><body>captcha</body></html>",
                url,
            ),
        }
    )

    result = try_content_fallbacks(url, transport)  # type: ignore[arg-type]

    assert result is None


def test_reader_uses_content_fallback_after_exhaustion() -> None:
    url = "https://example.com/post"
    jina_url = "https://r.jina.ai/https://example.com/post"
    reader = UnlimitedSearchReader()
    reader.transport = FakeTransport(  # type: ignore[assignment]
        {
            url: ResponseEnvelope(403, "blocked", url),
            jina_url: ResponseEnvelope(
                200,
                json.dumps({"data": {"content": "Fallback markdown content. " * 8}}),
                jina_url,
                headers={"content-type": "application/json"},
            ),
        }
    )

    result = reader.read_public_url(url, enable_public_routes=False, max_attempts=0)

    assert result.ok is True
    assert result.verdict == Verdict.WEAK_OK
    assert result.summary == "content fallback succeeded: jina-json"
    assert result.metadata["platform"] == "content-fallback"
    assert result.metadata["route"] == "jina-json"
    assert result.metadata["fallback_verdict"] == "weak_ok"
    assert result.metadata["recovery_fallbacks"]["content_fallback"] == "hit"


def test_reader_records_recovery_metadata_when_fallbacks_are_exhausted() -> None:
    reader = UnlimitedSearchReader()
    reader.transport = FakeTransport({})  # type: ignore[assignment]

    result = reader.read_public_url(
        "https://example.com/missing",
        enable_public_routes=False,
        max_attempts=0,
    )

    assert result.ok is False
    assert result.metadata["recovery_fallbacks"] == {
        "gate_stop_reason": "exhausted",
        "content_fallback": "miss",
        "archive_fallback": "miss",
    }
