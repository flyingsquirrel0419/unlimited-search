# unlimited-search

English | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md)

Python MCP server and CLI for reading public web content through public-only routes, browser-like HTTP identities, non-browser content fallbacks, public archive fallbacks, and media metadata extraction.

`unlimited-search` is public-content tooling. It is not intended to bypass logins, paywalls, CAPTCHA, private networks, or access controls.

## How It Reads

`read_public_url` tries these layers in order:

1. Platform public routes for known sites such as Reddit, X/Twitter, Bluesky, Hacker News, Google News, Stack Overflow, Wikipedia, GitHub, npm, PyPI, Wayback, and others.
2. A generic HTTP grid with browser-like TLS identities, URL variants, referer strategies, response validation, and HTTP/1.1 curl fallback for selected transport failures.
3. Non-browser content fallbacks:
   - Jina Reader JSON content
   - RSS/Atom discovery through Jina `external.alternate`
   - common origin feed paths such as `/feed`, `/rss`, `/atom.xml`
   - OGP, JSON-LD, Schema.org, and Next.js payload metadata salvage
4. Public archive fallbacks:
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshots
5. `yt-dlp` metadata extraction for known public media hosts.

See [Platform coverage](PLATFORMS.md) for the current support matrix and known gaps.

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

## Commands

```bash
unlimited-search serve
unlimited-search read https://example.com
unlimited-search read https://example.com --max-attempts 0
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
unlimited-search help
```

Notes:

- `read` returns content, trace, verdict, and metadata.
- `diagnose` returns the compact trace without full content.
- `media` uses `yt-dlp --dump-json` and does not download media.
- `--max-attempts 0` skips the generic HTTP grid, which is useful for forcing content fallback smoke tests.
- Fallback successes are intentionally reported as `weak_ok` or `suspect_ok`, not `strong_ok`.

## MCP Config

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

## Development

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search serve
uv run pytest
```

## Tools

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

## Verification Examples

```bash
# Public-route smoke
uv run unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 300

# Jina fallback smoke
uv run unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 300

# RSS fallback smoke
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300

# Archive fallback smoke
uv run unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 300

# Full test suite
uv run pytest
```

## Live Eval Set

Use the live eval runner when changing routes or fallbacks and you want before/after evidence across real sites.

```bash
# Show eval cases
uv run python scripts/run_eval.py --list

# Run the full live set and write eval-results/eval-<timestamp>.jsonl
uv run python scripts/run_eval.py

# Also write human-readable reports
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv

# Run only stable/search routes
uv run python scripts/run_eval.py --group stable --group search

# Compare with a previous run
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

The default set lives in `scripts/eval_urls.yaml`. Difficult sites such as NamuWiki, TikTok, Naver Search, Amazon, and Google Scholar are marked optional so they produce warnings instead of failing the whole run when the remote site blocks or rate-limits automation.

## Project Docs

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
