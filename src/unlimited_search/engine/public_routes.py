from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, quote, unquote, urlsplit

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
    if platform == "media":
        return _media(url, _detect_media_platform(url) or "media", timeout=timeout)

    api_plan = _api_plan(url)
    if api_plan is not None:
        plan_platform, targets = api_plan
        return _first_structured_route(plan_platform, targets, transport, timeout=timeout)
    return None


def _detect_platform(url: str) -> str | None:
    host = _normalized_host(url)
    if host == "redd.it" or host.endswith("reddit.com"):
        return "reddit"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "x"
    if _detect_media_platform(url) is not None:
        return "media"
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


def _media(url: str, platform: str, *, timeout: int) -> PublicRouteResult:
    media = extract_media_metadata(url, timeout=max(timeout, 60))
    attempt = PublicRouteAttempt(
        platform,
        "yt-dlp",
        media.ok,
        status=200 if media.ok else 0,
        bytes=len(json.dumps(media.metadata)),
        note=media.error or "metadata",
    )
    content = json.dumps(media.metadata, ensure_ascii=False) if media.ok else ""
    return PublicRouteResult(
        platform,
        media.ok,
        "yt-dlp" if media.ok else None,
        content,
        url,
        [attempt],
        metadata=media.metadata,
    )


def _api_plan(url: str) -> tuple[str, list[tuple[str, str]]] | None:
    split = urlsplit(url)
    host = _normalized_host(url)
    path = split.path.strip("/")
    parts = [unquote(part) for part in path.split("/") if part]
    query = parse_qs(split.query)

    if host == "bsky.app" and len(parts) >= 2 and parts[0] == "profile":
        actor = parts[1]
        actor_q = quote(actor, safe="")
        return (
            "bluesky",
            [
                ("atproto-profile", f"https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={actor_q}"),
                ("atproto-author-feed", f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={actor_q}&limit=10"),
            ],
        )

    if host in MASTODON_INSTANCES:
        if parts and parts[0].startswith("@"):
            acct = quote(parts[0][1:], safe="")
            return ("mastodon", [("accounts-lookup", f"https://{host}/api/v1/accounts/lookup?acct={acct}")])
        return ("mastodon", [("instance", f"https://{host}/api/v1/instance")])

    if host == "news.ycombinator.com":
        item_id = query.get("id", [""])[0]
        if item_id:
            return ("hacker-news", [("algolia-item", f"https://hn.algolia.com/api/v1/items/{quote(item_id, safe='')}")])
        return ("hacker-news", [("firebase-topstories", "https://hacker-news.firebaseio.com/v0/topstories.json")])

    if host == "stackoverflow.com":
        site = "stackoverflow"
        if len(parts) >= 2 and parts[0] == "questions" and parts[1].isdigit():
            qid = parts[1]
            return (
                "stack-exchange",
                [
                    (
                        "question-with-body",
                        f"https://api.stackexchange.com/2.3/questions/{qid}?order=desc&sort=activity&site={site}&filter=withbody",
                    )
                ],
            )
        if len(parts) >= 2 and parts[0] == "questions" and parts[1] == "tagged":
            tag = quote(parts[2] if len(parts) >= 3 else "", safe="")
            if tag:
                return (
                    "stack-exchange",
                    [
                        (
                            "tagged-questions",
                            f"https://api.stackexchange.com/2.3/questions?order=desc&sort=activity&site={site}&pagesize=10&tagged={tag}",
                        )
                    ],
                )
        search = query.get("q", [""])[0] if parts[:1] == ["search"] else ""
        if search:
            return (
                "stack-exchange",
                [
                    (
                        "search",
                        f"https://api.stackexchange.com/2.3/search?order=desc&sort=votes&site={site}&pagesize=10&intitle={quote(search, safe='')}",
                    )
                ],
            )
        return (
            "stack-exchange",
            [("active-questions", f"https://api.stackexchange.com/2.3/questions?order=desc&sort=activity&site={site}&pagesize=10")],
        )

    if host == "lobste.rs":
        if len(parts) >= 2 and parts[0] == "t":
            return ("lobsters", [("tag-json", f"https://lobste.rs/t/{quote(parts[1], safe='')}.json")])
        if len(parts) >= 2 and parts[0] == "s":
            return ("lobsters", [("story-json", f"https://lobste.rs/s/{quote(parts[1], safe='')}.json")])
        return ("lobsters", [("hottest-json", "https://lobste.rs/hottest.json")])

    if host == "v2ex.com":
        if len(parts) >= 2 and parts[0] == "go":
            return ("v2ex", [("node-topics", f"https://www.v2ex.com/api/topics/show.json?node_name={quote(parts[1], safe='')}")])
        return ("v2ex", [("hot-topics", "https://www.v2ex.com/api/topics/hot.json")])

    if host == "dev.to":
        if len(parts) >= 2 and parts[0] == "t":
            return ("dev-to", [("tag-articles", f"https://dev.to/api/articles?tag={quote(parts[1], safe='')}&per_page=10")])
        if parts and parts[0].startswith("@"):
            return ("dev-to", [("user-articles", f"https://dev.to/api/articles?username={quote(parts[0][1:], safe='')}&per_page=10")])
        return ("dev-to", [("latest-articles", "https://dev.to/api/articles?per_page=10")])

    if host == "arxiv.org":
        if len(parts) >= 2 and parts[0] == "abs":
            return ("arxiv", [("atom-id", f"https://export.arxiv.org/api/query?id_list={quote(parts[1], safe='/.')}")])
        search = query.get("query", [""])[0] or query.get("search_query", [""])[0]
        if search:
            return ("arxiv", [("atom-search", f"https://export.arxiv.org/api/query?search_query=all:{quote(search, safe='')}&max_results=10")])

    if host in {"doi.org", "dx.doi.org"} and path:
        return ("crossref", [("works-doi", f"https://api.crossref.org/works/{quote(path, safe='/')}")])

    if host.endswith("wikipedia.org") and len(parts) >= 2 and parts[0] == "wiki":
        language = host.split(".", 1)[0] or "en"
        title = quote(parts[1], safe="")
        return ("wikipedia", [("rest-summary", f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{title}")])

    if host == "openlibrary.org":
        if len(parts) >= 2 and parts[0] == "isbn":
            isbn = quote(parts[1], safe="")
            return (
                "openlibrary",
                [("isbn-books", f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=data&format=json")],
            )
        if len(parts) >= 2 and parts[0] == "works":
            return ("openlibrary", [("work-json", f"https://openlibrary.org/works/{quote(parts[1], safe='')}.json")])
        search = query.get("q", [""])[0]
        if search:
            return ("openlibrary", [("search-json", f"https://openlibrary.org/search.json?q={quote(search, safe='')}&limit=10")])

    if host == "github.com" and len(parts) >= 2 and parts[0] not in GITHUB_RESERVED_PATHS:
        owner, repo = quote(parts[0], safe=""), quote(parts[1], safe="")
        if len(parts) >= 3 and parts[2] == "releases":
            return ("github", [("releases", f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=10")])
        if len(parts) >= 3 and parts[2] == "issues":
            return ("github", [("issues", f"https://api.github.com/repos/{owner}/{repo}/issues?per_page=10")])
        return ("github", [("repo", f"https://api.github.com/repos/{owner}/{repo}")])

    if host == "npmjs.com" and len(parts) >= 2 and parts[0] == "package":
        package = "/".join(parts[1:3]) if parts[1].startswith("@") and len(parts) >= 3 else parts[1]
        return ("npm", [("registry-latest", f"https://registry.npmjs.org/{quote(package, safe='@/')}/latest")])

    if host == "pypi.org" and len(parts) >= 2 and parts[0] == "project":
        return ("pypi", [("package-json", f"https://pypi.org/pypi/{quote(parts[1], safe='')}/json")])

    if host == "web.archive.org" and path.startswith("web/"):
        archived_url = path.split("/", 2)[2] if path.count("/") >= 2 else ""
        if archived_url.startswith(("http://", "https://")):
            return (
                "wayback",
                [("cdx", f"https://web.archive.org/cdx/search/cdx?url={quote(archived_url, safe=':/?&=%')}&output=json&limit=10")],
            )

    if host == "blog.naver.com" and len(parts) >= 2:
        return (
            "naver-blog",
            [
                (
                    "mobile-post",
                    f"https://m.blog.naver.com/PostView.naver?blogId={quote(parts[0], safe='')}&logNo={quote(parts[1], safe='')}",
                )
            ],
        )

    if _should_use_jina(url):
        return ("jina-reader", [("reader", f"https://r.jina.ai/http://{url}")])

    return None


def _first_structured_route(
    platform: str,
    targets: list[tuple[str, str]],
    transport: PublicTransport,
    *,
    timeout: int,
) -> PublicRouteResult:
    attempts: list[PublicRouteAttempt] = []
    for route, target in targets:
        result = transport.get(target, identity="safari", timeout=timeout)
        response = result.response
        ok = response is not None and _public_api_response_ok(response)
        attempts.append(_attempt_from_response(platform, route, ok, response, result.error))
        if ok and response is not None:
            return PublicRouteResult(platform, True, route, response.text, response.url, attempts)
    return PublicRouteResult(platform, False, attempts=attempts, final_url=targets[-1][1] if targets else "")


def _public_api_response_ok(response: ResponseEnvelope) -> bool:
    text = response.text.lstrip()
    lowered = text[:500].lower()
    if response.status_code != 200 or not text:
        return False
    if any(marker in lowered for marker in ("just a moment", "captcha", "access denied", "slardarwaf")):
        return False
    if text.startswith(("{", "[")):
        try:
            return json.loads(text) not in ({}, [], None, "")
        except Exception:
            return False
    if text.startswith("<?xml") or "<rss" in lowered or "<feed" in lowered:
        return True
    if lowered.startswith("title:") or "url source:" in lowered:
        return True
    return response.body_size >= 350


def _normalized_host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _detect_media_platform(url: str) -> str | None:
    host = _normalized_host(url)
    if host == "youtu.be" or host.endswith("youtube.com"):
        return "youtube"
    if host.endswith("vimeo.com"):
        return "vimeo"
    if host.endswith("soundcloud.com"):
        return "soundcloud"
    if host.endswith("twitch.tv"):
        return "twitch"
    if host.endswith("tiktok.com"):
        return "tiktok"
    if host.endswith("dailymotion.com") or host == "dai.ly":
        return "dailymotion"
    if host.endswith("rumble.com"):
        return "rumble"
    if host == "tv.naver.com" or host.endswith(".tv.naver.com"):
        return "naver-tv"
    if host.endswith("kakao.com"):
        return "kakao"
    if host.endswith("chzzk.naver.com"):
        return "chzzk"
    if host.endswith("sooplive.co.kr") or host.endswith("afreecatv.com"):
        return "soop"
    return None


def _should_use_jina(url: str) -> bool:
    host = _normalized_host(url)
    return (
        host.endswith("medium.com")
        or host.endswith("substack.com")
        or host in {"news.naver.com", "n.news.naver.com", "finance.naver.com"}
    )


MASTODON_INSTANCES = {
    "fosstodon.org",
    "hachyderm.io",
    "mastodon.online",
    "mastodon.social",
    "mstdn.social",
}

GITHUB_RESERVED_PATHS = {
    "about",
    "apps",
    "blog",
    "collections",
    "enterprise",
    "events",
    "features",
    "issues",
    "login",
    "marketplace",
    "new",
    "notifications",
    "orgs",
    "pricing",
    "pulls",
    "search",
    "settings",
    "sponsors",
    "topics",
    "trending",
}


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
