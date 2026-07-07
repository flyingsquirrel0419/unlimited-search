import unlimited_search.engine.reader as reader_module
from unlimited_search.engine.models import Verdict
from unlimited_search.engine.public_routes import PublicRouteAttempt, PublicRouteResult
from unlimited_search.engine.reader import UnlimitedSearchReader


def test_private_loopback_url_is_rejected() -> None:
    result = UnlimitedSearchReader().read_public_url(
        "http://127.0.0.1:8000/private",
        enable_public_routes=False,
        max_attempts=2,
    )

    assert result.ok is False
    assert result.verdict == Verdict.UNSAFE_URL
    assert result.stop_reason == "unsafe_url"


def test_private_loopback_url_is_rejected_before_zero_attempt_fallbacks() -> None:
    result = UnlimitedSearchReader().read_public_url(
        "http://127.0.0.1:8000/private",
        enable_public_routes=False,
        max_attempts=0,
    )

    assert result.ok is False
    assert result.verdict == Verdict.UNSAFE_URL
    assert result.stop_reason == "unsafe_url"
    assert [attempt.phase for attempt in result.trace] == ["safety"]


def test_jina_public_route_uses_weak_verdict(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_public_route(url, transport, *, timeout=20):  # type: ignore[no-untyped-def]
        return PublicRouteResult(
            "jina-reader",
            True,
            "reader",
            "Title: Example",
            "https://r.jina.ai/https://example.com/post",
            [PublicRouteAttempt("jina-reader", "reader", True, status=200, bytes=14, note="ok")],
        )

    monkeypatch.setattr(reader_module, "try_public_route", fake_public_route)

    result = UnlimitedSearchReader().read_public_url("https://example.com/post")

    assert result.ok is True
    assert result.verdict == Verdict.WEAK_OK
    assert result.trace[-1].verdict == Verdict.WEAK_OK
