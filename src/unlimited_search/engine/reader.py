from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Sequence
from urllib.parse import urlsplit

from .archive_fallbacks import try_archive_fallback
from .content_fallbacks import try_content_fallbacks
from .models import Attempt, FetchResult, ResponseEnvelope, TERMINAL_NONSUCCESS, Verdict
from .public_routes import try_public_route
from .safety import classify_url
from .transforms import identity_plan, interleave_attempts, iter_url_variants, referer_plan, referer_value
from .transport import PublicTransport
from .validators import validate_response


class UnlimitedSearchReader:
    def __init__(self, *, allow_private: bool = False) -> None:
        self.transport = PublicTransport(allow_private=allow_private)

    def read_public_url(
        self,
        url: str,
        *,
        success_selectors: Sequence[str] | None = None,
        timeout: int = 25,
        max_attempts: int = 12,
        enable_public_routes: bool = True,
        preferred_identity: str | None = None,
        max_content_chars: int | None = None,
    ) -> FetchResult:
        trace: list[Attempt] = []
        ok, reason = classify_url(url, allow_private=getattr(self.transport, "allow_private", False))
        if not ok:
            attempt = Attempt(
                phase="safety",
                executor="classify_url",
                url=url,
                verdict=Verdict.UNSAFE_URL,
                reasons=[reason],
                error=f"unsafe_url:{reason}",
            )
            trace.append(attempt)
            return _failure(trace, None, attempt, stop_reason=Verdict.UNSAFE_URL.value)

        if enable_public_routes:
            route_result = try_public_route(url, self.transport, timeout=min(timeout, 25))
            if route_result is not None:
                for route_attempt in route_result.attempts:
                    trace.append(
                        Attempt(
                            phase="public_route",
                            executor=route_attempt.route,
                            url=url,
                            status=route_attempt.status,
                            body_size=route_attempt.bytes,
                            verdict=_public_route_verdict(route_result.platform) if route_attempt.ok else Verdict.BLOCKED,
                            reasons=[route_attempt.note] if route_attempt.note else [],
                        )
                    )
                if route_result.ok:
                    content = _trim(route_result.content, max_content_chars)
                    verdict = _public_route_verdict(route_result.platform)
                    return FetchResult(
                        ok=True,
                        content=content,
                        final_url=route_result.final_url,
                        verdict=verdict,
                        summary=f"public route succeeded: {route_result.platform}:{route_result.route}",
                        trace=trace,
                        stop_reason="success",
                        metadata={
                            "platform": route_result.platform,
                            "route": route_result.route,
                            **route_result.metadata,
                        },
                    )

        plan = interleave_attempts(
            iter_url_variants(url),
            identity_plan(preferred_identity),
            referer_plan(),
        )
        if max_attempts >= 0:
            plan = plan[:max_attempts]

        best_suspect: tuple[ResponseEnvelope, Attempt] | None = None
        last_response: ResponseEnvelope | None = None
        last_attempt: Attempt | None = None

        for transform_name, target_url, identity, referer_strategy in plan:
            started = time.monotonic()
            ref = referer_value(referer_strategy, target_url)
            result = self.transport.get(target_url, identity=identity, referer=ref, timeout=timeout)
            attempt = Attempt(
                phase="grid",
                executor="curl_cffi" if identity else "http",
                url=target_url,
                url_transform=transform_name,
                identity=identity,
                referer=referer_strategy,
                elapsed_ms=result.elapsed_ms or int((time.monotonic() - started) * 1000),
            )
            if result.error or result.response is None:
                attempt.error = result.error or "no_response"
                attempt.verdict = Verdict.UNSAFE_URL if attempt.error.startswith("unsafe_url:") else Verdict.UNKNOWN
                trace.append(attempt)
                if attempt.verdict in TERMINAL_NONSUCCESS:
                    failure = _failure(
                        trace,
                        last_response,
                        last_attempt or attempt,
                        stop_reason=attempt.verdict.value,
                    )
                    return _with_recovery_fallbacks(
                        failure,
                        url,
                        self.transport,
                        timeout=timeout,
                        max_content_chars=max_content_chars,
                        last_response=last_response,
                    )
                continue

            response = result.response
            attempt.executor = _transport_name(response)
            validation = validate_response(
                response,
                success_selectors=success_selectors,
            )
            attempt.status = validation.status
            attempt.body_size = validation.body_size
            attempt.verdict = validation.verdict
            attempt.reasons = list(validation.reasons)
            trace.append(attempt)
            last_response = response
            last_attempt = attempt

            if validation.ok:
                return FetchResult(
                    ok=True,
                    content=_trim(response.text, max_content_chars),
                    final_url=response.url or target_url,
                    verdict=validation.verdict,
                    summary=f"{identity} + {transform_name} + referer:{referer_strategy} -> {validation.verdict.value}",
                    trace=trace,
                    stop_reason="success",
                )
            if validation.verdict == Verdict.SUSPECT_OK and best_suspect is None:
                best_suspect = (response, attempt)
            if validation.verdict in TERMINAL_NONSUCCESS:
                failure = _failure(trace, response, attempt, stop_reason=validation.verdict.value)
                return _with_recovery_fallbacks(
                    failure,
                    url,
                    self.transport,
                    timeout=timeout,
                    max_content_chars=max_content_chars,
                    last_response=response,
                )

        if best_suspect is not None:
            response, attempt = best_suspect
            failure = _failure(trace, response, attempt, stop_reason="suspect_only")
            failure.content = _trim(response.text, max_content_chars)
            return _with_recovery_fallbacks(
                failure,
                url,
                self.transport,
                timeout=timeout,
                max_content_chars=max_content_chars,
                last_response=response,
            )
        failure = _failure(trace, last_response, last_attempt, stop_reason="exhausted")
        return _with_recovery_fallbacks(
            failure,
            url,
            self.transport,
            timeout=timeout,
            max_content_chars=max_content_chars,
            last_response=last_response,
        )

    def read_public_urls(self, urls: Sequence[str], **kwargs: object) -> list[FetchResult]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for url in urls:
            grouped[_host(url)].append(url)
        results: list[FetchResult] = []
        for host_urls in grouped.values():
            for url in host_urls:
                results.append(self.read_public_url(url, **kwargs))
        return results

    def diagnose_access(self, url: str, **kwargs: object) -> FetchResult:
        kwargs.setdefault("max_content_chars", 2000)
        return self.read_public_url(url, **kwargs)


def _failure(
    trace: list[Attempt],
    response: ResponseEnvelope | None,
    attempt: Attempt | None,
    *,
    stop_reason: str,
) -> FetchResult:
    content = response.text if response is not None else ""
    final_url = response.url if response is not None else (attempt.url if attempt else "")
    verdict = attempt.verdict if attempt else Verdict.UNKNOWN
    untried_routes: list[str] = []
    if stop_reason not in {Verdict.AUTH_REQUIRED.value, Verdict.NOT_FOUND.value, Verdict.UNSAFE_URL.value}:
        untried_routes.append("browser_fallback: run with a Playwright-capable client if the page requires JavaScript challenge resolution")
        untried_routes.append("api_discovery: inspect browser network traffic for public JSON/rss/graphql endpoints")
    return FetchResult(
        ok=False,
        content=content,
        final_url=final_url,
        verdict=verdict,
        summary=f"failed after {len(trace)} attempts; stop={stop_reason}",
        trace=trace,
        stop_reason=stop_reason,
        untried_routes=untried_routes,
    )


def _with_recovery_fallbacks(
    failure: FetchResult,
    original_url: str,
    transport: PublicTransport,
    *,
    timeout: int,
    max_content_chars: int | None,
    last_response: ResponseEnvelope | None,
) -> FetchResult:
    recovery = {
        "gate_stop_reason": failure.stop_reason,
        "content_fallback": "skipped",
        "archive_fallback": "skipped",
    }
    if failure.stop_reason in {Verdict.AUTH_REQUIRED.value, Verdict.UNSAFE_URL.value}:
        failure.metadata["recovery_fallbacks"] = recovery
        return failure

    if failure.stop_reason != Verdict.NOT_FOUND.value:
        recovery["content_fallback"] = "tried"
        fallback = try_content_fallbacks(
            original_url,
            transport,
            timeout=min(timeout, 25),
            max_content_chars=max_content_chars,
            last_response=last_response,
        )
        if fallback is not None:
            recovery["content_fallback"] = "hit"
            return _fallback_fetch_result(
                failure,
                platform="content-fallback",
                phase="content_fallback",
                route=fallback.route,
                content=fallback.content,
                source_url=fallback.source_url,
                content_type=fallback.content_type,
                attempts=[attempt.to_dict() for attempt in fallback.attempts],
                metadata=fallback.metadata,
                reason="content_fallback",
                recovery=recovery,
            )
        recovery["content_fallback"] = "miss"

    recovery["archive_fallback"] = "tried"
    archive = try_archive_fallback(
        original_url,
        transport,
        timeout=min(timeout, 25),
        max_content_chars=max_content_chars,
    )
    if archive is not None:
        recovery["archive_fallback"] = "hit"
        return _fallback_fetch_result(
            failure,
            platform="archive-fallback",
            phase="archive_fallback",
            route=archive.route,
            content=archive.content,
            source_url=archive.source_url,
            content_type=archive.content_type,
            attempts=[attempt.to_dict() for attempt in archive.attempts],
            metadata=archive.metadata,
            reason="archive_fallback",
            recovery=recovery,
        )

    recovery["archive_fallback"] = "miss"
    failure.metadata["recovery_fallbacks"] = recovery
    return failure


def _fallback_fetch_result(
    failure: FetchResult,
    *,
    platform: str,
    phase: str,
    route: str,
    content: str,
    source_url: str,
    content_type: str,
    attempts: list[dict[str, object]],
    metadata: dict[str, object],
    reason: str,
    recovery: dict[str, str],
) -> FetchResult:
    trace = list(failure.trace)
    last_attempt = attempts[-1] if attempts else {}
    verdict = _fallback_verdict(platform, route)
    trace.append(
        Attempt(
            phase=phase,
            executor=route,
            url=source_url,
            status=int(last_attempt.get("status") or 0),
            body_size=len(content.encode("utf-8", "ignore")),
            verdict=verdict,
            reasons=[reason],
        )
    )
    return FetchResult(
        ok=True,
        content=content,
        final_url=source_url,
        verdict=verdict,
        summary=f"{platform.replace('-', ' ')} succeeded: {route}",
        trace=trace,
        stop_reason="success",
        untried_routes=[],
        metadata={
            "platform": platform,
            "route": route,
            "source_url": source_url,
            "content_type": content_type,
            "fallback_attempts": attempts,
            "fallback_verdict": verdict.value,
            "origin_stop_reason": failure.stop_reason,
            "recovery_fallbacks": dict(recovery),
            **metadata,
        },
    )


def _fallback_verdict(platform: str, route: str) -> Verdict:
    if platform == "content-fallback" and route == "metadata-salvage":
        return Verdict.SUSPECT_OK
    return Verdict.WEAK_OK


def _trim(text: str, max_chars: int | None) -> str:
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[:max_chars]


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _transport_name(response: ResponseEnvelope) -> str:
    for key, value in response.headers.items():
        if key.lower() == "x-unlimited-search-transport":
            return value
    return "curl_cffi"


def _public_route_verdict(platform: str) -> Verdict:
    weak_platforms = {
        "jina-reader",
        "youtube",
        "vimeo",
        "soundcloud",
        "twitch",
        "tiktok",
        "dailymotion",
        "rumble",
        "naver-tv",
        "kakao",
        "chzzk",
        "soop",
        "naver-search",
        "amazon",
    }
    if platform in weak_platforms:
        return Verdict.WEAK_OK
    return Verdict.STRONG_OK
