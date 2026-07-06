from unlimited_search.engine.media import MediaResult
from unlimited_search.engine.models import ResponseEnvelope
import unlimited_search.engine.public_routes as public_routes
from unlimited_search.engine.public_routes import try_public_route
from unlimited_search.engine.transport import TransportResult


class FakeTransport:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        self.urls.append(url)
        if url.endswith("/.rss"):
            return TransportResult(
                ResponseEnvelope(200, "<rss><channel><title>x</title></channel></rss>", url)
            )
        if "r.jina.ai" in url:
            return TransportResult(ResponseEnvelope(200, "Title: Example\n\nURL Source: https://example.com/", url))
        return TransportResult(ResponseEnvelope(200, '{"ok": true}', url))


def test_reddit_rss_public_route() -> None:
    transport = FakeTransport()
    result = try_public_route("https://www.reddit.com/r/python", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "reddit"
    assert result.route == "rss"


def test_bluesky_profile_routes_to_atproto() -> None:
    transport = FakeTransport()
    result = try_public_route("https://bsky.app/profile/bsky.app", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "bluesky"
    assert result.route == "atproto-profile"
    assert transport.urls[0] == "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor=bsky.app"


def test_hacker_news_item_routes_to_algolia() -> None:
    transport = FakeTransport()
    result = try_public_route("https://news.ycombinator.com/item?id=123", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "hacker-news"
    assert result.route == "algolia-item"
    assert transport.urls == ["https://hn.algolia.com/api/v1/items/123"]


def test_stackoverflow_question_routes_to_stack_exchange_api() -> None:
    transport = FakeTransport()
    result = try_public_route("https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "stack-exchange"
    assert result.route == "question-with-body"
    assert transport.urls[0].startswith("https://api.stackexchange.com/2.3/questions/11227809")


def test_registry_project_routes() -> None:
    transport = FakeTransport()
    npm = try_public_route("https://www.npmjs.com/package/react", transport)  # type: ignore[arg-type]
    pypi = try_public_route("https://pypi.org/project/requests/", transport)  # type: ignore[arg-type]

    assert npm is not None and npm.platform == "npm"
    assert pypi is not None and pypi.platform == "pypi"
    assert "https://registry.npmjs.org/react/latest" in transport.urls
    assert "https://pypi.org/pypi/requests/json" in transport.urls


def test_jina_reader_route_for_medium() -> None:
    transport = FakeTransport()
    result = try_public_route("https://medium.com/example/post", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "jina-reader"
    assert result.route == "reader"
    assert transport.urls == ["https://r.jina.ai/http://https://medium.com/example/post"]


def test_wayback_archive_routes_to_cdx() -> None:
    transport = FakeTransport()
    result = try_public_route("https://web.archive.org/web/20200101000000/https://example.com", transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "wayback"
    assert result.route == "cdx"
    assert transport.urls == ["https://web.archive.org/cdx/search/cdx?url=https://example.com&output=json&limit=10"]


def test_media_host_routes_through_yt_dlp(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_extract(url: str, *, timeout: int = 90) -> MediaResult:
        return MediaResult(True, url, metadata={"title": "x", "extractor": "vimeo"})

    monkeypatch.setattr(public_routes, "extract_media_metadata", fake_extract)
    result = try_public_route("https://vimeo.com/76979871", FakeTransport())  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "vimeo"
    assert result.route == "yt-dlp"
