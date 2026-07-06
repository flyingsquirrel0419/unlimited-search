from unlimited_search.engine.transport import _parse_curl_include_response, _should_try_http1_fallback


def test_http2_timeout_errors_trigger_http1_fallback() -> None:
    assert _should_try_http1_fallback("Timeout:Operation timed out after 25002 milliseconds")
    assert _should_try_http1_fallback("HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR")
    assert not _should_try_http1_fallback("unsafe_url:private_ip")


def test_parse_curl_include_response_uses_last_response_block() -> None:
    raw = (
        b"HTTP/1.1 301 Moved Permanently\r\nLocation: https://example.com/\r\n\r\n"
        b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n"
        b"<html>ok</html>"
    )

    response = _parse_curl_include_response(raw, "https://example.com/")

    assert response.status_code == 200
    assert response.text == "<html>ok</html>"
    assert response.headers["Content-Type"] == "text/html; charset=UTF-8"
