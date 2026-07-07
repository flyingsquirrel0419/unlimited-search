from unlimited_search.engine.models import Verdict
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
