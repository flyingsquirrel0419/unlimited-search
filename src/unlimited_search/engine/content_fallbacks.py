from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import ResponseEnvelope
from .transport import PublicTransport


MIN_TEXT_CHARS = 80


@dataclass(slots=True)
class ContentFallbackAttempt:
    route: str
    url: str
    ok: bool
    status: int = 0
    bytes: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "route": self.route,
            "url": self.url,
            "ok": self.ok,
            "status": self.status,
            "bytes": self.bytes,
            "note": self.note,
        }


@dataclass(slots=True)
class ContentFallbackResult:
    ok: bool
    route: str
    content: str
    source_url: str
    content_type: str
    attempts: list[ContentFallbackAttempt] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def try_content_fallbacks(
    url: str,
    transport: PublicTransport,
    *,
    timeout: int = 20,
    max_content_chars: int | None = None,
    last_response: ResponseEnvelope | None = None,
) -> ContentFallbackResult | None:
    attempts: list[ContentFallbackAttempt] = []
    feed_candidates: list[str] = []

    jina_url = _jina_url(url)
    jina_result = transport.get(
        jina_url,
        identity="safari",
        timeout=timeout,
        extra_headers={"Accept": "application/json"},
    )
    jina_response = jina_result.response
    jina_data = _parse_jina_json(jina_response.text) if jina_response and jina_response.status_code == 200 else None
    jina_ok = bool(jina_data and _useful_text(jina_data.get("content", "")))
    attempts.append(_attempt("jina-json", jina_url, jina_ok, jina_response, jina_result.error))
    if jina_data:
        feed_candidates.extend(_alternate_feed_urls(jina_data))
    if jina_ok and jina_data is not None:
        content = _trim(str(jina_data.get("content") or ""), max_content_chars)
        return ContentFallbackResult(
            True,
            "jina-json",
            content,
            jina_url,
            "markdown",
            attempts,
            metadata={
                "title": jina_data.get("title"),
                "description": jina_data.get("description"),
                "url": jina_data.get("url"),
            },
        )

    for feed_url in _dedupe(feed_candidates + _feed_candidate_urls(url)):
        feed_result = transport.get(feed_url, identity="safari", timeout=timeout)
        feed_response = feed_result.response
        feed = _parse_feed(feed_response.text, feed_response.url or feed_url) if feed_response and feed_response.status_code == 200 else None
        ok = feed is not None
        attempts.append(_attempt("rss-discovery", feed_url, ok, feed_response, feed_result.error))
        if ok and feed is not None:
            content = json.dumps(feed, ensure_ascii=False, indent=2)
            return ContentFallbackResult(
                True,
                "rss-discovery",
                _trim(content, max_content_chars),
                feed_url,
                "feed_json",
                attempts,
                metadata={"entry_count": len(feed.get("entries", []))},
            )

    metadata_source = last_response
    if metadata_source is None:
        direct_result = transport.get(url, identity="safari", timeout=timeout)
        metadata_source = direct_result.response
        attempts.append(_attempt("metadata-fetch", url, metadata_source is not None, metadata_source, direct_result.error))

    if metadata_source is not None:
        extracted = {} if _looks_like_challenge_html(metadata_source.text) else extract_metadata(metadata_source.text)
        metadata_ok = _metadata_is_useful(extracted)
        attempts.append(_attempt("metadata-salvage", metadata_source.url or url, metadata_ok, metadata_source, None))
        if metadata_ok:
            content = json.dumps(extracted, ensure_ascii=False, indent=2)
            return ContentFallbackResult(
                True,
                "metadata-salvage",
                _trim(content, max_content_chars),
                metadata_source.url or url,
                "metadata_json",
                attempts,
                metadata={"metadata_keys": sorted(extracted)},
            )

    return None


def extract_metadata(html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    metadata: dict[str, Any] = {}
    meta = _extract_meta_tags(soup)
    if meta:
        metadata["meta"] = meta
    json_ld = _extract_json_ld(soup)
    if json_ld:
        metadata["json_ld"] = json_ld
    next_text = _extract_next_text(html_text)
    if _useful_text(next_text):
        metadata["next_text"] = next_text[:4000]
    return metadata


def _parse_jina_json(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except Exception:
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else None


def _alternate_feed_urls(data: dict[str, Any]) -> list[str]:
    external = data.get("external")
    if not isinstance(external, dict):
        return []
    alternate = external.get("alternate")
    if not isinstance(alternate, list):
        return []
    urls: list[str] = []
    for item in alternate:
        href = ""
        kind = ""
        if isinstance(item, str):
            href = item
        elif isinstance(item, dict):
            href = str(item.get("href") or item.get("url") or "")
            kind = str(item.get("type") or item.get("rel") or "")
        lowered = f"{href} {kind}".lower()
        if href.startswith(("http://", "https://")) and any(token in lowered for token in ("rss", "atom", "feed", "xml")):
            urls.append(href)
    return urls


def _feed_candidate_urls(url: str) -> list[str]:
    split = urlsplit(url)
    if split.scheme not in {"http", "https"} or not split.netloc:
        return []
    origin = f"{split.scheme}://{split.netloc}"
    return [
        urljoin(origin, "/rss"),
        urljoin(origin, "/feed"),
        urljoin(origin, "/atom.xml"),
        urljoin(origin, "/rss.xml"),
        urljoin(origin, "/index.xml"),
    ]


def _parse_feed(text: str, source_url: str) -> dict[str, Any] | None:
    stripped = (text or "").lstrip()
    lowered = stripped[:300].lower()
    if not ("<rss" in lowered or "<feed" in lowered or stripped.startswith("<?xml")):
        return None
    try:
        root = ET.fromstring(stripped)
    except Exception:
        return None
    tag = _local_name(root.tag)
    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return None
        entries = []
        for item in channel.findall("item")[:20]:
            entries.append(
                {
                    "title": _child_text(item, "title"),
                    "link": _child_text(item, "link"),
                    "summary": _child_text(item, "description"),
                    "published": _child_text(item, "pubDate"),
                }
            )
        entries = [entry for entry in entries if entry.get("title") or entry.get("link")]
        if not entries:
            return None
        return {
            "feed": {"title": _child_text(channel, "title"), "url": source_url},
            "entries": entries,
        }
    if tag == "feed":
        entries = []
        for entry in _children(root, "entry")[:20]:
            entries.append(
                {
                    "title": _child_text(entry, "title"),
                    "link": _atom_link(entry),
                    "summary": _child_text(entry, "summary") or _child_text(entry, "content"),
                    "published": _child_text(entry, "published") or _child_text(entry, "updated"),
                }
            )
        entries = [entry for entry in entries if entry.get("title") or entry.get("link")]
        if not entries:
            return None
        return {
            "feed": {"title": _child_text(root, "title"), "url": source_url},
            "entries": entries,
        }
    return None


def _extract_meta_tags(soup: BeautifulSoup) -> dict[str, str]:
    keys = {
        "description",
        "og:title",
        "og:description",
        "og:type",
        "og:url",
        "og:image",
        "twitter:title",
        "twitter:description",
        "twitter:image",
    }
    values: dict[str, str] = {}
    if soup.title and soup.title.string:
        values["title"] = soup.title.string.strip()
    for tag in soup.find_all("meta"):
        name = str(tag.get("property") or tag.get("name") or "").strip()
        content = str(tag.get("content") or "").strip()
        if name in keys and content:
            values[name] = content
    return values


def _extract_json_ld(soup: BeautifulSoup) -> list[Any]:
    values: list[Any] = []
    for script in soup.find_all("script"):
        script_type = str(script.get("type") or "").lower()
        if "ld+json" not in script_type:
            continue
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        values.append(parsed)
        if len(values) >= 5:
            break
    return values


def _extract_next_text(html_text: str) -> str:
    chunks = re.findall(r"self\.__next_f\.push\(\[1,\"(.*?)\"\]\)", html_text or "", flags=re.S)
    if not chunks:
        return ""
    joined = "".join(chunks)
    try:
        decoded = joined.encode("utf-8").decode("unicode_escape", "ignore")
    except Exception:
        decoded = joined
    decoded = html.unescape(decoded)
    decoded = re.sub(r"\\n|\\t|\\r", " ", decoded)
    decoded = re.sub(r"\s+", " ", decoded)
    return decoded.strip()


def _metadata_is_useful(metadata: dict[str, Any]) -> bool:
    meta = metadata.get("meta")
    if isinstance(meta, dict) and any(
        meta.get(key) for key in ("og:title", "og:description", "description", "twitter:title", "twitter:description")
    ):
        return True
    json_ld = metadata.get("json_ld")
    if isinstance(json_ld, list) and bool(json_ld):
        return True
    next_text = metadata.get("next_text")
    return isinstance(next_text, str) and _useful_text(next_text)


def _looks_like_challenge_html(text: str) -> bool:
    lowered = (text or "")[:2000].lower()
    return any(
        marker in lowered
        for marker in (
            "just a moment",
            "attention required! | cloudflare",
            "checking your browser",
            "captcha",
            "access denied",
            "slardarwaf",
        )
    )


def _attempt(
    route: str,
    url: str,
    ok: bool,
    response: ResponseEnvelope | None,
    error: str | None,
) -> ContentFallbackAttempt:
    if response is None:
        return ContentFallbackAttempt(route, url, False, note=error or "no_response")
    return ContentFallbackAttempt(
        route,
        response.url or url,
        ok,
        status=response.status_code,
        bytes=response.body_size,
        note="ok" if ok else error or "fallback_failed",
    )


def _child_text(element: ET.Element, child_name: str) -> str:
    for child in list(element):
        if _local_name(child.tag) == child_name:
            return "".join(child.itertext()).strip()
    return ""


def _children(element: ET.Element, child_name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == child_name]


def _atom_link(entry: ET.Element) -> str:
    for child in list(entry):
        if _local_name(child.tag) == "link":
            href = child.attrib.get("href", "")
            if href:
                return href
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _jina_url(url: str) -> str:
    return f"https://r.jina.ai/http://{url}"


def _useful_text(text: object) -> bool:
    return isinstance(text, str) and len(text.strip()) >= MIN_TEXT_CHARS


def _trim(text: str, max_chars: int | None) -> str:
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[:max_chars]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
