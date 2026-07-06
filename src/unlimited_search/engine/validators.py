from __future__ import annotations

import json
import re
from collections.abc import Sequence

from bs4 import BeautifulSoup

from .models import ResponseEnvelope, ValidationResult, Verdict

HARD_CHALLENGE_MARKERS = (
    "sec-if-cpt-container",
    "powered and protected by akamai",
    "just a moment...",
    "cf-chl-bypass",
    "attention required! | cloudflare",
    "<title>bot challenge</title>",
    "the requested url was rejected",
    "request unsuccessful. incapsula",
    "please enable js and disable any ad blocker",
    "px-captcha",
    "slardarwaf",
    "_wafchallengeid",
    "waforiginalreid",
    "waf-aiso",
)

SOFT_CHALLENGE_MARKERS = (
    "access denied",
    "checking your browser",
    "captcha",
    "datadome",
)

LOGIN_MARKERS = (
    "sign in to continue",
    "log in to continue",
    "login required",
    "please log in",
    "subscribe to continue",
    "paywall",
)

SMALL_BODY_THRESHOLD = 350


def validate_response(
    response: ResponseEnvelope,
    *,
    success_selectors: Sequence[str] | None = None,
    known_bad_sizes: Sequence[int] | None = None,
) -> ValidationResult:
    text = response.text or ""
    lowered = text.lower()
    size = response.body_size
    status = int(response.status_code or 0)
    result = ValidationResult(verdict=Verdict.UNKNOWN, body_size=size, status=status)

    if status == 429:
        result.verdict = Verdict.RATE_LIMITED
        result.reasons.append("status=429")
        return result
    if status in {401, 407}:
        result.verdict = Verdict.AUTH_REQUIRED
        result.reasons.append(f"status={status}")
        return result
    if status in {404, 410}:
        result.verdict = Verdict.NOT_FOUND
        result.reasons.append(f"status={status}")
        return result
    if status >= 500:
        result.verdict = Verdict.BLOCKED
        result.reasons.append(f"status={status}")
        return result
    if status == 0:
        result.verdict = Verdict.UNKNOWN
        result.reasons.append("status=0")
        return result

    hard_hits = [marker for marker in HARD_CHALLENGE_MARKERS if marker.lower() in lowered]
    if hard_hits:
        result.verdict = Verdict.CHALLENGE
        result.reasons.extend(f"hard:{marker}" for marker in hard_hits[:3])
        return result

    if known_bad_sizes:
        for bad_size in known_bad_sizes:
            if abs(size - bad_size) <= 20:
                result.verdict = Verdict.CHALLENGE
                result.reasons.append(f"known_bad_size:{size}")
                return result

    if _looks_like_json(text, response.headers):
        parsed = _json_is_nonempty(text)
        if parsed is True and 200 <= status < 400:
            result.verdict = Verdict.WEAK_OK
            result.reasons.append("json_ok")
            return result
        if parsed is False:
            result.verdict = Verdict.SUSPECT_OK
            result.reasons.append("empty_json")
            return result

    selectors = list(success_selectors or [])
    if selectors:
        hits = _selector_hits(text, selectors)
        if hits:
            result.verdict = Verdict.STRONG_OK
            result.matched_selectors.extend(hits)
            result.reasons.append("selector_match")
            return result

    login_hits = [marker for marker in LOGIN_MARKERS if marker in lowered]
    if login_hits and _looks_like_auth_wall(text, size):
        result.verdict = Verdict.AUTH_REQUIRED
        result.reasons.append("auth_or_paywall_marker")
        return result

    soft_hits = [marker for marker in SOFT_CHALLENGE_MARKERS if marker in lowered]
    nonterminal_soft_reasons: list[str] = []
    if soft_hits:
        if 200 <= status < 300 and _has_public_content_signals(text, size):
            nonterminal_soft_reasons.extend(f"soft_nonterminal:{marker}" for marker in soft_hits[:3])
        else:
            result.verdict = Verdict.SUSPECT_OK if 200 <= status < 400 else Verdict.CHALLENGE
            result.reasons.extend(f"soft:{marker}" for marker in soft_hits[:3])
            return result

    if 300 <= status < 400:
        result.verdict = Verdict.SUSPECT_OK
        result.reasons.append(f"redirect_status:{status}")
        return result
    if status in {403, 406, 451}:
        result.verdict = Verdict.BLOCKED
        result.reasons.append(f"status={status}")
        return result
    if 200 <= status < 300:
        if size < SMALL_BODY_THRESHOLD and not _looks_complete_short_page(text):
            result.verdict = Verdict.SUSPECT_OK
            result.reasons.append(f"small_body:{size}")
            return result
        if login_hits:
            result.reasons.append("login_marker_nonterminal")
        result.reasons.extend(nonterminal_soft_reasons)
        result.verdict = Verdict.WEAK_OK
        result.reasons.append("clean_2xx")
        return result

    result.verdict = Verdict.BLOCKED
    result.reasons.append(f"status={status}")
    return result


def _looks_like_json(text: str, headers: dict[str, str]) -> bool:
    content_type = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            content_type = value.lower()
            break
    stripped = text.lstrip()
    return "json" in content_type or stripped.startswith("{") or stripped.startswith("[")


def _json_is_nonempty(text: str) -> bool | None:
    try:
        value = json.loads(text)
    except Exception:
        return None
    return value not in (None, {}, [], "")


def _selector_hits(html: str, selectors: Sequence[str]) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    hits: list[str] = []
    for selector in selectors:
        try:
            if soup.select(selector):
                hits.append(selector)
        except Exception:
            continue
    return hits


def _looks_complete_short_page(text: str) -> bool:
    lowered = text.lower()
    if "</html>" not in lowered and "</body>" not in lowered:
        return False
    visible = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    visible = re.sub(r"(?s)<[^>]+>", " ", visible)
    visible = re.sub(r"\s+", " ", visible).strip()
    return len(visible) >= 32


def _looks_like_auth_wall(text: str, size: int) -> bool:
    if size > 20_000:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in ("<article", "<main", "og:title", "json-ld")):
        return False
    auth_terms = sum(term in lowered for term in ("password", "sign in", "log in", "subscribe"))
    return auth_terms >= 2 or size < 5_000


def _has_public_content_signals(text: str, size: int) -> bool:
    if size < 20_000:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in ("<main", "<article", "og:title", "application/ld+json")):
        return True
    return "<title" in lowered and _visible_text_len(text) >= 80


def _visible_text_len(text: str) -> int:
    visible = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", text)
    visible = re.sub(r"(?s)<[^>]+>", " ", visible)
    visible = re.sub(r"\s+", " ", visible).strip()
    return len(visible)
