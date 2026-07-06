from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

from .media import extract_media_metadata
from .models import ResponseEnvelope
from .transport import PublicTransport


@dataclass(slots=True)
class PublicRouteAttempt:
    platform: str
    route: str
    ok: bool
    status: int = 0
    bytes: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "platform": self.platform,
            "route": self.route,
            "ok": self.ok,
            "status": self.status,
            "bytes": self.bytes,
            "note": self.note,
        }


@dataclass(slots=True)
class PublicRouteResult:
    platform: str
    ok: bool
    route: str | None = None
    content: str = ""
    final_url: str = ""
    attempts: list[PublicRouteAttempt] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


def try_public_route(url: str, transport: PublicTransport, *, timeout: int = 20) -> PublicRouteResult | None:
    platform = _detect_platform(url)
    if platform == "reddit":
        return _reddit(url, transport, timeout=timeout)
    if platform == "x":
        return _x(url, transport, timeout=timeout)
    if platform == "youtube":
        return _youtube(url, timeout=timeout)
    return None


def _detect_platform(url: str) -> str | None:
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host == "redd.it" or host.endswith("reddit.com"):
        return "reddit"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "x"
    if host == "youtu.be" or host.endswith("youtube.com"):
        return "youtube"
    return None


def _reddit(url: str, transport: PublicTransport, *, timeout: int) -> PublicRouteResult:
    attempts: list[PublicRouteAttempt] = []
    base = url.split("?", 1)[0].rstrip("/")
    rss_url = base + (".rss" if "/comments/" in base else "/.rss")
    json_url = base + (".json" if "/comments/" in base else "/.json")

    for route, target in (("rss", rss_url), ("json", json_url)):
        result = transport.get(target, identity="safari", timeout=timeout)
        response = result.response
        ok = response is not None and _reddit_response_ok(route, response)
        attempts.append(_attempt_from_response("reddit", route, ok, response, result.error))
        if ok and response is not None:
            return PublicRouteResult("reddit", True, route, response.text, response.url, attempts)
    return PublicRouteResult("reddit", False, attempts=attempts, final_url=url)


def _reddit_response_ok(route: str, response: ResponseEnvelope) -> bool:
    text = response.text.lstrip()
    if response.status_code != 200:
        return False
    if route == "rss":
        return "<rss" in text[:200].lower() or "<feed" in text[:200].lower()
    return text.startswith("{") or text.startswith("[")


TWEET_ID_RE = re.compile(r"/status(?:es)?/(\d+)")


def _x(url: str, transport: PublicTransport, *, timeout: int) -> PublicRouteResult:
    attempts: list[PublicRouteAttempt] = []
    match = TWEET_ID_RE.search(url)
    if match:
        tweet_id = match.group(1)
        targets = [
            ("tweet-result", f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=a"),
            ("oembed", f"https://publish.twitter.com/oembed?url={quote(f'https://twitter.com/i/status/{tweet_id}', safe='')}&omit_script=1"),
        ]
    else:
        handle = urlsplit(url).path.strip("/").split("/", 1)[0]
        if not handle or handle.lower() in {"i", "search", "home", "explore", "messages", "settings"}:
            return PublicRouteResult("x", False, attempts=attempts, final_url=url)
        targets = [("syndication-profile", f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}")]

    for route, target in targets:
        result = transport.get(target, identity="safari", timeout=timeout)
        response = result.response
        ok = response is not None and _x_response_ok(route, response)
        attempts.append(_attempt_from_response("x", route, ok, response, result.error))
        if ok and response is not None:
            return PublicRouteResult("x", True, route, response.text, response.url, attempts)
    return PublicRouteResult("x", False, attempts=attempts, final_url=url)


def _x_response_ok(route: str, response: ResponseEnvelope) -> bool:
    if response.status_code != 200:
        return False
    text = response.text
    if route in {"tweet-result", "oembed"}:
        try:
            data = json.loads(text)
        except Exception:
            return False
        return bool(data.get("text") or data.get("html"))
    return "__NEXT_DATA__" in text or "timeline" in text.lower()


def _youtube(url: str, *, timeout: int) -> PublicRouteResult:
    media = extract_media_metadata(url, timeout=max(timeout, 60))
    attempt = PublicRouteAttempt(
        "youtube",
        "yt-dlp",
        media.ok,
        status=200 if media.ok else 0,
        bytes=len(json.dumps(media.metadata)),
        note=media.error or "metadata",
    )
    content = json.dumps(media.metadata, ensure_ascii=False) if media.ok else ""
    return PublicRouteResult(
        "youtube",
        media.ok,
        "yt-dlp" if media.ok else None,
        content,
        url,
        [attempt],
        metadata=media.metadata,
    )


def _attempt_from_response(
    platform: str,
    route: str,
    ok: bool,
    response: ResponseEnvelope | None,
    error: str | None,
) -> PublicRouteAttempt:
    if response is None:
        return PublicRouteAttempt(platform, route, False, note=error or "no_response")
    return PublicRouteAttempt(
        platform,
        route,
        ok,
        status=response.status_code,
        bytes=response.body_size,
        note="ok" if ok else error or "route_failed",
    )
