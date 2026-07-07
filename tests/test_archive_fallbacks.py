import json

from unlimited_search.engine.archive_fallbacks import try_archive_fallback
from unlimited_search.engine.models import ResponseEnvelope
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


def _html(label: str) -> str:
    return f"<html><head><title>{label}</title></head><body><article>{label}</article>{'x' * 500}</body></html>"


def test_wayback_available_snapshot_succeeds() -> None:
    url = "https://example.com/missing"
    available_url = "https://archive.org/wayback/available?url=https%3A%2F%2Fexample.com%2Fmissing"
    snapshot_url = "https://web.archive.org/web/20200101000000/https://example.com/missing"
    transport = FakeTransport(
        {
            available_url: ResponseEnvelope(
                200,
                json.dumps({"archived_snapshots": {"closest": {"available": True, "status": "200", "url": snapshot_url}}}),
                available_url,
            ),
            snapshot_url: ResponseEnvelope(200, _html("Archived"), snapshot_url),
        }
    )

    result = try_archive_fallback(url, transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.route == "wayback-available"
    assert result.source_url == snapshot_url
    assert "Archived" in result.content


def test_wayback_cdx_snapshot_succeeds_after_available_and_latest_fail() -> None:
    url = "https://example.com/deleted"
    available_url = "https://archive.org/wayback/available?url=https%3A%2F%2Fexample.com%2Fdeleted"
    latest_url = "https://web.archive.org/web/https://example.com/deleted"
    cdx_url = (
        "https://web.archive.org/cdx/search/cdx?"
        "url=https://example.com/deleted&output=json&fl=timestamp,original,statuscode,mimetype&filter=statuscode:200&limit=1&sort=reverse"
    )
    snapshot_url = "https://web.archive.org/web/20240202000000/https://example.com/deleted"
    transport = FakeTransport(
        {
            available_url: ResponseEnvelope(200, json.dumps({"archived_snapshots": {}}), available_url),
            latest_url: ResponseEnvelope(404, "not found", latest_url),
            cdx_url: ResponseEnvelope(
                200,
                json.dumps([["timestamp", "original", "statuscode", "mimetype"], ["20240202000000", url, "200", "text/html"]]),
                cdx_url,
            ),
            snapshot_url: ResponseEnvelope(200, _html("CDX Archived"), snapshot_url),
        }
    )

    result = try_archive_fallback(url, transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.route == "wayback-cdx"
    assert result.source_url == snapshot_url


def test_archive_today_succeeds_after_wayback_paths_fail() -> None:
    url = "https://example.com/article"
    available_url = "https://archive.org/wayback/available?url=https%3A%2F%2Fexample.com%2Farticle"
    latest_url = "https://web.archive.org/web/https://example.com/article"
    cdx_url = (
        "https://web.archive.org/cdx/search/cdx?"
        "url=https://example.com/article&output=json&fl=timestamp,original,statuscode,mimetype&filter=statuscode:200&limit=1&sort=reverse"
    )
    archive_url = "https://archive.ph/newest/https://example.com/article"
    transport = FakeTransport(
        {
            available_url: ResponseEnvelope(200, json.dumps({"archived_snapshots": {}}), available_url),
            latest_url: ResponseEnvelope(404, "not found", latest_url),
            cdx_url: ResponseEnvelope(200, json.dumps([["timestamp", "original", "statuscode", "mimetype"]]), cdx_url),
            archive_url: ResponseEnvelope(200, _html("Archive Today"), archive_url),
        }
    )

    result = try_archive_fallback(url, transport)  # type: ignore[arg-type]

    assert result is not None
    assert result.route == "archive-today"
    assert result.metadata["archive_host"] == "archive.ph"


def test_archive_challenge_response_is_not_success() -> None:
    url = "https://example.com/blocked"
    available_url = "https://archive.org/wayback/available?url=https%3A%2F%2Fexample.com%2Fblocked"
    snapshot_url = "https://web.archive.org/web/20200101000000/https://example.com/blocked"
    transport = FakeTransport(
        {
            available_url: ResponseEnvelope(
                200,
                json.dumps({"archived_snapshots": {"closest": {"available": True, "status": "200", "url": snapshot_url}}}),
                available_url,
            ),
            snapshot_url: ResponseEnvelope(200, "<html><title>Just a moment...</title><body>captcha</body></html>" + ("x" * 500), snapshot_url),
        }
    )

    result = try_archive_fallback(url, transport)  # type: ignore[arg-type]

    assert result is None


def test_reader_uses_archive_fallback_for_not_found() -> None:
    url = "https://example.com/missing"
    available_url = "https://archive.org/wayback/available?url=https%3A%2F%2Fexample.com%2Fmissing"
    snapshot_url = "https://web.archive.org/web/20200101000000/https://example.com/missing"
    reader = UnlimitedSearchReader()
    reader.transport = FakeTransport(  # type: ignore[assignment]
        {
            url: ResponseEnvelope(404, "not found", url),
            "https://r.jina.ai/https://example.com/missing": ResponseEnvelope(404, "not found", "https://r.jina.ai/https://example.com/missing"),
            "https://example.com/rss": None,
            "https://example.com/feed": None,
            "https://example.com/atom.xml": None,
            "https://example.com/rss.xml": None,
            "https://example.com/index.xml": None,
            available_url: ResponseEnvelope(
                200,
                json.dumps({"archived_snapshots": {"closest": {"available": True, "status": "200", "url": snapshot_url}}}),
                available_url,
            ),
            snapshot_url: ResponseEnvelope(200, _html("Archived Missing"), snapshot_url),
        }
    )

    result = reader.read_public_url(url, enable_public_routes=False, max_attempts=1)

    assert result.ok is True
    assert result.summary == "archive fallback succeeded: wayback-available"
    assert result.metadata["platform"] == "archive-fallback"
    assert result.metadata["route"] == "wayback-available"
