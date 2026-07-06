from __future__ import annotations

import time
import urllib.error
import urllib.request
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .models import ResponseEnvelope
from .safety import DEFAULT_MAX_REDIRECTS, classify_url, resolve_redirect


class TransportError(RuntimeError):
    pass


@dataclass(slots=True)
class TransportResult:
    response: ResponseEnvelope | None
    error: str | None = None
    elapsed_ms: int = 0


@dataclass
class SessionPool:
    _sessions: dict[tuple[str, str], Any] = field(default_factory=dict)

    def get(self, host: str, identity: str) -> Any | None:
        try:
            from curl_cffi import requests as curl_requests
        except Exception:
            return None
        key = (host, identity)
        session = self._sessions.get(key)
        if session is None:
            try:
                session = curl_requests.Session(impersonate=identity)
            except Exception:
                return None
            self._sessions[key] = session
        return session

    def reset(self) -> None:
        for session in self._sessions.values():
            try:
                session.close()
            except Exception:
                pass
        self._sessions.clear()


class PublicTransport:
    def __init__(self, *, allow_private: bool = False, max_redirects: int = DEFAULT_MAX_REDIRECTS) -> None:
        self.allow_private = allow_private
        self.max_redirects = max_redirects
        self.pool = SessionPool()

    def get(
        self,
        url: str,
        *,
        identity: str = "safari",
        referer: str = "",
        timeout: int = 25,
        extra_headers: dict[str, str] | None = None,
    ) -> TransportResult:
        started = time.monotonic()
        ok, reason = classify_url(url, allow_private=self.allow_private)
        if not ok:
            return TransportResult(None, f"unsafe_url:{reason}", _elapsed(started))

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
            "User-Agent": _user_agent(identity),
        }
        if referer:
            headers["Referer"] = referer
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = self._get_following(url, identity=identity, headers=headers, timeout=timeout)
            return TransportResult(response, None, _elapsed(started))
        except Exception as exc:
            first_error = f"{type(exc).__name__}:{str(exc)[:240]}"
            if _should_try_http1_fallback(first_error):
                fallback = self._http1_cli_fallback(url, headers=headers, timeout=timeout)
                if fallback.response is not None:
                    return TransportResult(fallback.response, None, _elapsed(started))
                if fallback.error:
                    first_error = f"{first_error}; http1_fallback:{fallback.error}"
            return TransportResult(None, first_error, _elapsed(started))

    def _get_following(
        self,
        url: str,
        *,
        identity: str,
        headers: dict[str, str],
        timeout: int,
    ) -> ResponseEnvelope:
        current = url
        for _ in range(self.max_redirects + 1):
            response = self._single_get(current, identity=identity, headers=headers, timeout=timeout)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = _header_get(response.headers, "location")
                if not location:
                    return response
                next_url = resolve_redirect(current, location)
                ok, reason = classify_url(next_url, allow_private=self.allow_private)
                if not ok:
                    raise TransportError(f"unsafe_redirect:{reason}")
                current = next_url
                continue
            return response
        raise TransportError("too_many_redirects")

    def _single_get(self, url: str, *, identity: str, headers: dict[str, str], timeout: int) -> ResponseEnvelope:
        host = urllib.parse.urlsplit(url).hostname or "unknown"
        session = self.pool.get(host, identity)
        if session is not None:
            response = session.get(url, headers=headers, timeout=timeout, allow_redirects=False)
            envelope = _from_curl_response(response)
            envelope.headers.setdefault("x-unlimited-search-transport", "curl_cffi")
            return envelope
        envelope = _urllib_get(url, headers=headers, timeout=timeout)
        envelope.headers.setdefault("x-unlimited-search-transport", "urllib")
        return envelope

    def _http1_cli_fallback(self, url: str, *, headers: dict[str, str], timeout: int) -> TransportResult:
        started = time.monotonic()
        ok, reason = classify_url(url, allow_private=self.allow_private)
        if not ok:
            return TransportResult(None, f"unsafe_url:{reason}", _elapsed(started))
        fallback_headers = dict(headers)
        fallback_headers["User-Agent"] = _user_agent("chrome")
        fallback_headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        fallback_timeout = max(timeout, 35)
        cmd = ["curl", "--http1.1", "-L", "-sS", "-i", "--max-time", str(fallback_timeout), url]
        for key in ("User-Agent", "Accept", "Accept-Language"):
            value = fallback_headers.get(key)
            if value:
                cmd[1:1] = ["-H", f"{key}: {value}"]
        try:
            proc = subprocess.run(cmd, text=False, capture_output=True, timeout=fallback_timeout + 5)
        except FileNotFoundError:
            return TransportResult(None, "curl_not_available", _elapsed(started))
        except subprocess.TimeoutExpired:
            return TransportResult(None, f"timeout:{fallback_timeout}s", _elapsed(started))
        raw = proc.stdout or b""
        if not raw:
            err = (proc.stderr or b"").decode("utf-8", "replace")[:240]
            return TransportResult(None, err or f"curl_exit:{proc.returncode}", _elapsed(started))
        try:
            response = _parse_curl_include_response(raw, url)
        except Exception as exc:
            return TransportResult(None, f"parse_error:{type(exc).__name__}:{str(exc)[:160]}", _elapsed(started))
        response.headers.setdefault("x-unlimited-search-transport", "curl_http1_cli")
        return TransportResult(response, None, _elapsed(started))


def _from_curl_response(response: Any) -> ResponseEnvelope:
    headers = {str(k): str(v) for k, v in dict(getattr(response, "headers", {}) or {}).items()}
    cookies: dict[str, str] = {}
    try:
        for cookie in response.cookies.jar:
            cookies[cookie.name] = cookie.value
    except Exception:
        try:
            cookies = {str(k): str(v) for k, v in dict(response.cookies).items()}
        except Exception:
            cookies = {}
    content = bytes(getattr(response, "content", b"") or b"")
    text = getattr(response, "text", "") or content.decode("utf-8", "replace")
    return ResponseEnvelope(
        status_code=int(getattr(response, "status_code", 0) or 0),
        text=text,
        url=str(getattr(response, "url", "") or ""),
        headers=headers,
        cookies=cookies,
        content=content,
    )


def _urllib_get(url: str, *, headers: dict[str, str], timeout: int) -> ResponseEnvelope:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):  # type: ignore[no-untyped-def]
            return None

    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(request, timeout=timeout) as response:
            content = response.read()
            final_url = response.geturl()
            status = response.status
            response_headers = dict(response.headers.items())
    except urllib.error.HTTPError as error:
        content = error.read()
        final_url = error.geturl()
        status = error.code
        response_headers = dict(error.headers.items())
    text = content.decode(_charset_from_headers(response_headers), "replace")
    return ResponseEnvelope(
        status_code=status,
        text=text,
        url=final_url,
        headers=response_headers,
        cookies={},
        content=content,
    )


def _parse_curl_include_response(raw: bytes, requested_url: str) -> ResponseEnvelope:
    blocks = raw.split(b"\r\n\r\n")
    if len(blocks) == 1:
        blocks = raw.split(b"\n\n")
    header_block = b""
    body_parts: list[bytes] = []
    for index, block in enumerate(blocks):
        if block.startswith(b"HTTP/"):
            header_block = block
            body_parts = blocks[index + 1 :]
    if not header_block:
        raise TransportError("missing_http_header")
    header_lines = header_block.decode("iso-8859-1", "replace").splitlines()
    status_line = header_lines[0]
    try:
        status = int(status_line.split()[1])
    except Exception as exc:
        raise TransportError(f"bad_status_line:{status_line}") from exc
    headers: dict[str, str] = {}
    for line in header_lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    body = b"\r\n\r\n".join(body_parts)
    text = body.decode(_charset_from_headers(headers), "replace")
    return ResponseEnvelope(
        status_code=status,
        text=text,
        url=requested_url,
        headers=headers,
        cookies={},
        content=body,
    )


def _charset_from_headers(headers: dict[str, str]) -> str:
    content_type = _header_get(headers, "content-type")
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip() or "utf-8"
    return "utf-8"


def _header_get(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def _elapsed(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _should_try_http1_fallback(error: str) -> bool:
    lowered = error.lower()
    return (
        "timed out" in lowered
        or "timeout" in lowered
        or "http/2 stream" in lowered
        or "internal_error" in lowered
        or "0 bytes" in lowered
    )


def _user_agent(identity: str) -> str:
    if "android" in identity:
        return (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
        )
    if "ios" in identity or "safari" in identity:
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
        )
    if "firefox" in identity:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
