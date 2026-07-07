# unlimited-search

English | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md)

[![test](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml/badge.svg)](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

<p align="center">
  <img src="assets/hero.png" width="860" alt="unlimited-search hero showing public URLs routed through routes, HTTP, RSS, archives, and media into clean structured text for MCP and CLI.">
</p>

`unlimited-search` is a Python CLI and MCP server for reading public web content when a normal direct fetch is not enough. It combines platform public routes, browser-like HTTP identities, content fallbacks, public archive fallbacks, and media metadata extraction behind one local tool.

It is built for agents and automation that need usable text from public URLs. It is not intended to bypass logins, paywalls, CAPTCHA, private networks, account restrictions, IP bans, or access controls.

## Quickstart

Prerequisite: Python 3.12 or newer.

```bash
python -m pip install unlimited-search
unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 800
```

The command returns JSON with page `content`, a `verdict`, request `metadata`, and an attempt `trace`.

For MCP clients, install the package and register the stdio server:

```json
{
  "mcpServers": {
    "unlimited-search": {
      "command": "unlimited-search",
      "args": ["serve"]
    }
  }
}
```

## What It Provides

| Capability | What it does |
| --- | --- |
| Public platform routes | Uses unauthenticated public APIs, feeds, or metadata routes before generic fetching. |
| Browser-like fetching | Tries multiple TLS/browser identities, URL variants, referer strategies, and response validation. |
| Content fallbacks | Recovers public text through Jina Reader, RSS/Atom discovery, and embedded page metadata. |
| Archive fallbacks | Falls back to Wayback and archive.today/archive.ph public snapshots when live reads fail. |
| Media metadata | Uses `yt-dlp --dump-json` for public media URLs without downloading media. |
| MCP tools | Exposes single-URL reads, batch reads, diagnostics, and media extraction to MCP clients. |

See [Platform coverage](PLATFORMS.md) for the full support matrix and known gaps.

## Install

Install from PyPI:

```bash
python -m pip install unlimited-search
```

Update:

```bash
python -m pip install --upgrade unlimited-search
```

Remove:

```bash
python -m pip uninstall unlimited-search
```

## CLI Usage

```bash
unlimited-search help
unlimited-search read URL
unlimited-search diagnose URL
unlimited-search media URL
unlimited-search serve
```

Common examples:

```bash
unlimited-search read https://example.com --max-content-chars 1000
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Fallback-focused smoke tests:

```bash
unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 500
unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 500
```

Useful flags:

| Flag | Applies to | Purpose |
| --- | --- | --- |
| `--timeout SECONDS` | `read`, `diagnose`, `media` | Set request timeout. |
| `--max-attempts N` | `read`, `diagnose` | Limit generic HTTP-grid attempts. |
| `--max-content-chars N` | `read` | Limit returned content size. |
| `--no-public-routes` | `read`, `diagnose` | Skip platform public routes. |
| `--preferred-identity NAME` | `read`, `diagnose` | Try a specific browser-like identity first. |
| `--success-selector CSS` | `read` | Treat matching CSS selectors as success signals. Can be repeated. |

## MCP Tools

The MCP server runs over stdio:

```bash
unlimited-search serve
```

Available tools:

| Tool | Purpose |
| --- | --- |
| `read_public_url` | Read one public URL and return content, verdict, metadata, and trace. |
| `read_public_urls` | Read multiple public URLs in one tool call. |
| `diagnose_access` | Return a compact diagnosis and attempt trace without full content. |
| `extract_media` | Extract public media metadata through `yt-dlp` without downloading media. |

More configuration examples are in [MCP configuration](docs/mcp-config.md).

## How Reads Work

<p align="center">
  <img src="assets/pipeline.png" width="860" alt="Pipeline diagram: Public URL to platform routes, HTTP grid, content fallbacks, archive fallbacks, media metadata, and clean public text, with login, paywall, or CAPTCHA stopping safely.">
</p>

`read_public_url` tries the least invasive public routes first, then progressively broader recovery paths:

1. Platform-specific public routes for sites such as Reddit, X/Twitter, Bluesky, Hacker News, Google News, Stack Overflow, Wikipedia, GitHub, npm, PyPI, Wayback, Naver, Amazon, and Google Scholar.
2. A generic HTTP grid with browser-like TLS identities, URL variants, referer strategies, response validation, and selected HTTP/1.1 transport fallback.
3. Non-browser content fallbacks:
   - Jina Reader JSON content
   - RSS/Atom discovery through Jina `external.alternate`
   - common origin feed paths such as `/feed`, `/rss`, and `/atom.xml`
   - OGP, JSON-LD, Schema.org, and Next.js payload metadata salvage
4. Public archive fallbacks:
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshots
5. `yt-dlp` metadata extraction for known public media hosts.

Fallback successes are reported as `weak_ok` or `suspect_ok`, not `strong_ok`, because recovered content can be incomplete, stale, or metadata-only.

## Safety Boundaries

`unlimited-search` is a public-content reader. It should stop or report failure when a target requires authentication, payment, CAPTCHA, private network access, or hard anti-abuse bypassing.

The reader rejects private, loopback, link-local, multicast, reserved, and metadata-service targets by default. Redirects are checked before fallback routes are allowed to continue.

Returned HTML, JSON, RSS, archive text, and metadata should be treated as untrusted content.

## Development

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com --max-content-chars 300
uv run unlimited-search serve
uv run pytest
uv build
```

Run the live eval set when changing routes or fallback behavior:

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

The default eval cases live in [scripts/eval_urls.yaml](scripts/eval_urls.yaml). Difficult sites such as NamuWiki, TikTok, Naver Search, Amazon, and Google Scholar are optional so remote blocking or rate limits do not fail the whole run.

## Project Docs

- [Platform coverage](PLATFORMS.md)
- [MCP configuration](docs/mcp-config.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)
