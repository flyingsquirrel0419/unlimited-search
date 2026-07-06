from unlimited_search.engine.models import ResponseEnvelope
from unlimited_search.engine.public_routes import try_public_route
from unlimited_search.engine.transport import TransportResult


class FakeTransport:
    def get(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        if url.endswith("/.rss"):
            return TransportResult(
                ResponseEnvelope(200, "<rss><channel><title>x</title></channel></rss>", url)
            )
        return TransportResult(ResponseEnvelope(403, "blocked", url))


def test_reddit_rss_public_route() -> None:
    result = try_public_route("https://www.reddit.com/r/python", FakeTransport())  # type: ignore[arg-type]

    assert result is not None
    assert result.ok is True
    assert result.platform == "reddit"
    assert result.route == "rss"

