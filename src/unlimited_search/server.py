from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .engine.media import extract_media_metadata
from .engine.reader import UnlimitedSearchReader

mcp = FastMCP("unlimited-search")


def _reader() -> UnlimitedSearchReader:
    return UnlimitedSearchReader(allow_private=False)


@mcp.tool()
def read_public_url(
    url: str,
    success_selectors: list[str] | None = None,
    timeout: int = 25,
    max_attempts: int = 12,
    max_content_chars: int = 120000,
    enable_public_routes: bool = True,
    preferred_identity: str | None = None,
) -> dict[str, Any]:
    """Read one public URL through public routes and browser-like HTTP identities."""
    result = _reader().read_public_url(
        url,
        success_selectors=success_selectors,
        timeout=timeout,
        max_attempts=max_attempts,
        max_content_chars=max_content_chars,
        enable_public_routes=enable_public_routes,
        preferred_identity=preferred_identity,
    )
    return result.to_dict()


@mcp.tool()
def read_public_urls(
    urls: list[str],
    success_selectors: list[str] | None = None,
    timeout: int = 25,
    max_attempts: int = 8,
    max_content_chars: int = 60000,
    enable_public_routes: bool = True,
    preferred_identity: str | None = None,
) -> dict[str, Any]:
    """Read multiple public URLs, reusing host sessions within one tool call."""
    reader = _reader()
    results = reader.read_public_urls(
        urls,
        timeout=timeout,
        max_attempts=max_attempts,
        max_content_chars=max_content_chars,
        enable_public_routes=enable_public_routes,
        preferred_identity=preferred_identity,
        success_selectors=success_selectors,
    )
    return {
        "count": len(results),
        "results": [result.to_dict() for result in results],
    }


@mcp.tool()
def diagnose_access(
    url: str,
    timeout: int = 25,
    max_attempts: int = 12,
    enable_public_routes: bool = True,
    preferred_identity: str | None = None,
) -> dict[str, Any]:
    """Return a compact access diagnosis and attempt trace for one public URL."""
    result = _reader().diagnose_access(
        url,
        timeout=timeout,
        max_attempts=max_attempts,
        max_content_chars=2000,
        enable_public_routes=enable_public_routes,
        preferred_identity=preferred_identity,
    )
    data = result.to_dict()
    data["content"] = ""
    return data


@mcp.tool()
def extract_media(url: str, timeout: int = 90) -> dict[str, Any]:
    """Extract public media metadata using yt-dlp without downloading media."""
    return extract_media_metadata(url, timeout=timeout).to_dict()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
