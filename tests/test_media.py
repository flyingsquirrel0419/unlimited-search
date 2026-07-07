from unlimited_search.engine.media import extract_media_metadata


def test_media_extraction_rejects_loopback_url_before_yt_dlp() -> None:
    result = extract_media_metadata("http://127.0.0.1/video")

    assert result.ok is False
    assert result.error == "unsafe_url:private_ip"


def test_media_extraction_rejects_non_http_url_before_yt_dlp() -> None:
    result = extract_media_metadata("file:///etc/passwd")

    assert result.ok is False
    assert result.error == "unsafe_url:unsupported_scheme"
