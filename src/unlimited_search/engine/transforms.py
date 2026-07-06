from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit, urlunsplit


def iter_url_variants(url: str) -> list[tuple[str, str]]:
    candidates = [
        ("original", url),
        ("mobile_subdomain", _mobile_subdomain(url)),
        ("drop_www", _drop_www(url)),
    ]
    seen: set[str] = set()
    variants: list[tuple[str, str]] = []
    for name, value in candidates:
        if not value or value in seen:
            continue
        seen.add(value)
        variants.append((name, value))
    return variants


def identity_plan(preferred_identity: str | None = None) -> list[str]:
    identities = ["safari", "chrome", "chrome_android", "safari_ios", "firefox"]
    if preferred_identity and preferred_identity in identities:
        return [preferred_identity] + [identity for identity in identities if identity != preferred_identity]
    return identities


def referer_plan() -> list[str]:
    return ["self_root", "google_search", "none"]


def referer_value(strategy: str, url: str) -> str:
    if strategy == "none":
        return ""
    if strategy == "google_search":
        return "https://www.google.com/"
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/", "", ""))


def interleave_attempts(
    variants: Iterable[tuple[str, str]],
    identities: Iterable[str],
    referers: Iterable[str],
) -> list[tuple[str, str, str, str]]:
    variants_list = list(variants)
    identities_list = list(identities)
    referers_list = list(referers)
    out: list[tuple[str, str, str, str]] = []
    for referer in referers_list:
        for variant_name, variant_url in variants_list:
            for identity in identities_list:
                out.append((variant_name, variant_url, identity, referer))
    return out


def _replace_host(url: str, new_host: str) -> str:
    parts = urlsplit(url)
    if parts.port:
        new_host = f"{new_host}:{parts.port}"
    return urlunsplit(parts._replace(netloc=new_host))


def _mobile_subdomain(url: str) -> str | None:
    host = urlsplit(url).hostname or ""
    if host.startswith("www."):
        return _replace_host(url, "m." + host[4:])
    if host.count(".") == 1 and not host.startswith("m."):
        return _replace_host(url, "m." + host)
    return None


def _drop_www(url: str) -> str | None:
    host = urlsplit(url).hostname or ""
    if not host.startswith("www."):
        return None
    return _replace_host(url, host[4:])
