# Changelog

All notable changes to `unlimited-search` will be documented here.

## 0.1.0 - Unreleased

- Added MCP stdio server with `read_public_url`, `read_public_urls`, `diagnose_access`, and `extract_media`.
- Added resilient public-route readers for Reddit, X/Twitter, and YouTube metadata.
- Added browser-like HTTP fetching with TLS impersonation through `curl_cffi`.
- Added HTTP/1.1 curl fallback for timeout and HTTP/2 failure cases.
- Added SSRF checks for private, loopback, link-local, and metadata redirects.
- Added install/update/uninstall scripts for macOS, Linux, and Windows PowerShell.
