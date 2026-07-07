from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from .models import ResponseEnvelope
from .transport import PublicTransport


MIN_ARCHIVE_BODY_CHARS = 350
ARCHIVE_TODAY_HOSTS = ("archive.ph", "archive.today", "archive.is", "archive.md", "archive.vn", "archive.li")


@dataclass(slots=True)
class ArchiveFallbackAttempt:
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
class ArchiveFallbackResult:
    ok: bool
    route: str
    content: str
    source_url: str
    content_type: str
    attempts: list[ArchiveFallbackAttempt] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def try_archive_fallback(
    url: str,
    transport: PublicTransport,
    *,
    timeout: int = 20,
    max_content_chars: int | None = None,
) -> ArchiveFallbackResult | None:
    attempts: list[ArchiveFallbackAttempt] = []

    available_url = f"https://archive.org/wayback/available?url={quote(url, safe='')}"
    available_result = transport.get(available_url, identity="safari", timeout=timeout)
    available_response = available_result.response
    available_snapshot = _snapshot_from_available(available_response.text) if available_response else ""
    attempts.append(_attempt("wayback-available-api", available_url, bool(available_snapshot), available_response, available_result.error))
    if available_snapshot:
        result = _fetch_archive_snapshot("wayback-available", available_snapshot, transport, attempts, timeout, max_content_chars)
        if result is not None:
            return result

    latest_url = f"https://web.archive.org/web/{url}"
    latest_result = transport.get(latest_url, identity="safari", timeout=timeout)
    latest_response = latest_result.response
    latest_ok = latest_response is not None and _archive_response_ok(latest_response)
    attempts.append(_attempt("wayback-latest", latest_url, latest_ok, latest_response, latest_result.error))
    if latest_ok and latest_response is not None:
        return _result(
            "wayback-latest",
            latest_response.text,
            latest_response.url or latest_url,
            attempts,
            max_content_chars,
        )

    cdx_url = (
        "https://web.archive.org/cdx/search/cdx?"
        f"url={quote(url, safe=':/?&=%')}&output=json&fl=timestamp,original,statuscode,mimetype&filter=statuscode:200&limit=1&sort=reverse"
    )
    cdx_result = transport.get(cdx_url, identity="safari", timeout=timeout)
    cdx_response = cdx_result.response
    cdx_snapshot = _snapshot_from_cdx(cdx_response.text) if cdx_response else ""
    attempts.append(_attempt("wayback-cdx-api", cdx_url, bool(cdx_snapshot), cdx_response, cdx_result.error))
    if cdx_snapshot:
        result = _fetch_archive_snapshot("wayback-cdx", cdx_snapshot, transport, attempts, timeout, max_content_chars)
        if result is not None:
            return result

    for host in ARCHIVE_TODAY_HOSTS:
        archive_url = f"https://{host}/newest/{quote(url, safe=':/?&=%')}"
        archive_result = transport.get(archive_url, identity="safari", timeout=timeout)
        archive_response = archive_result.response
        archive_ok = archive_response is not None and _archive_response_ok(archive_response)
        attempts.append(_attempt("archive-today", archive_url, archive_ok, archive_response, archive_result.error))
        if archive_ok and archive_response is not None:
            return _result(
                "archive-today",
                archive_response.text,
                archive_response.url or archive_url,
                attempts,
                max_content_chars,
                metadata={"archive_host": host},
            )

    return None


def _fetch_archive_snapshot(
    route: str,
    snapshot_url: str,
    transport: PublicTransport,
    attempts: list[ArchiveFallbackAttempt],
    timeout: int,
    max_content_chars: int | None,
) -> ArchiveFallbackResult | None:
    snapshot_result = transport.get(snapshot_url, identity="safari", timeout=timeout)
    snapshot_response = snapshot_result.response
    snapshot_ok = snapshot_response is not None and _archive_response_ok(snapshot_response)
    attempts.append(_attempt(route, snapshot_url, snapshot_ok, snapshot_response, snapshot_result.error))
    if not snapshot_ok or snapshot_response is None:
        return None
    return _result(route, snapshot_response.text, snapshot_response.url or snapshot_url, attempts, max_content_chars)


def _snapshot_from_available(text: str) -> str:
    try:
        payload = json.loads(text)
    except Exception:
        return ""
    closest = payload.get("archived_snapshots", {}).get("closest") if isinstance(payload, dict) else None
    if not isinstance(closest, dict):
        return ""
    if closest.get("available") is False:
        return ""
    status = str(closest.get("status") or "")
    url = str(closest.get("url") or "")
    return url if url.startswith(("http://", "https://")) and status in {"", "200"} else ""


def _snapshot_from_cdx(text: str) -> str:
    try:
        rows = json.loads(text)
    except Exception:
        return ""
    if not isinstance(rows, list) or len(rows) < 2:
        return ""
    row = rows[1]
    if not isinstance(row, list) or len(row) < 2:
        return ""
    timestamp = str(row[0] or "")
    original = str(row[1] or "")
    if not timestamp or not original.startswith(("http://", "https://")):
        return ""
    return f"https://web.archive.org/web/{timestamp}/{original}"


def _archive_response_ok(response: ResponseEnvelope) -> bool:
    if response.status_code != 200:
        return False
    text = response.text or ""
    lowered = text[:3000].lower()
    if len(text.strip()) < MIN_ARCHIVE_BODY_CHARS:
        return False
    if any(
        marker in lowered
        for marker in (
            "wayback machine doesn't have that page archived",
            "this url has been excluded from the wayback machine",
            "page cannot be displayed",
            "checking your browser",
            "captcha",
            "just a moment",
            "access denied",
            "slardarwaf",
        )
    ):
        return False
    return True


def _result(
    route: str,
    content: str,
    source_url: str,
    attempts: list[ArchiveFallbackAttempt],
    max_content_chars: int | None,
    *,
    metadata: dict[str, Any] | None = None,
) -> ArchiveFallbackResult:
    return ArchiveFallbackResult(
        True,
        route,
        _trim(content, max_content_chars),
        source_url,
        "archive_html",
        list(attempts),
        metadata=metadata or {},
    )


def _attempt(
    route: str,
    url: str,
    ok: bool,
    response: ResponseEnvelope | None,
    error: str | None,
) -> ArchiveFallbackAttempt:
    if response is None:
        return ArchiveFallbackAttempt(route, url, False, note=error or "no_response")
    return ArchiveFallbackAttempt(
        route,
        response.url or url,
        ok,
        status=response.status_code,
        bytes=response.body_size,
        note="ok" if ok else error or "archive_failed",
    )


def _trim(text: str, max_chars: int | None) -> str:
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[:max_chars]
