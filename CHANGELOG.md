# Changelog

All notable changes to `unlimited-search` will be documented here.

## 0.1.0 - Unreleased

- Added MCP stdio server with `read_public_url`, `read_public_urls`, `diagnose_access`, and `extract_media`.
- Added resilient public-route readers for Reddit, X/Twitter, and YouTube metadata.
- Added first-pass platform public routes for Bluesky, Mastodon, Hacker News, Stack Overflow, Lobste.rs, V2EX, dev.to, arXiv, CrossRef, Wikipedia, OpenLibrary, GitHub, npm, PyPI, Wayback, Naver Blog, and Jina Reader fallbacks.
- Broadened automatic media routing beyond YouTube for known `yt-dlp`-supported public media hosts.
- Added non-browser content fallbacks for Jina Reader JSON, RSS/Atom discovery, and OGP/JSON-LD/Next.js metadata salvage.
- Added public archive fallbacks for Wayback Available, Wayback latest/CDX snapshots, and archive.today/archive.ph best-effort snapshots.
- Added browser-like HTTP fetching with TLS impersonation through `curl_cffi`.
- Added HTTP/1.1 curl fallback for timeout and HTTP/2 failure cases.
- Added SSRF checks for private, loopback, link-local, and metadata redirects.
- Added install/update/uninstall scripts for macOS, Linux, and Windows PowerShell.
- Refreshed user docs, platform coverage, troubleshooting guidance, MCP config notes, and GitHub templates.
