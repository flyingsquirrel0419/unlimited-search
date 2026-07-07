# unlimited-search

Python MCP server and CLI for reading public web content through public-only routes, browser-like HTTP identities, non-browser content fallbacks, and media metadata extraction.

`unlimited-search` is public-content tooling. It is not intended to bypass logins, paywalls, CAPTCHA, private networks, or access controls.

## How It Reads

`read_public_url` tries these layers in order:

1. Platform public routes for known sites such as Reddit, X/Twitter, Bluesky, Hacker News, Stack Overflow, Wikipedia, GitHub, npm, PyPI, Wayback, and others.
2. A generic HTTP grid with browser-like TLS identities, URL variants, referer strategies, response validation, and HTTP/1.1 curl fallback for selected transport failures.
3. Non-browser content fallbacks:
   - Jina Reader JSON content
   - RSS/Atom discovery through Jina `external.alternate`
   - common origin feed paths such as `/feed`, `/rss`, `/atom.xml`
   - OGP, JSON-LD, Schema.org, and Next.js payload metadata salvage
4. `yt-dlp` metadata extraction for known public media hosts.

See [Platform coverage](PLATFORMS.md) for the current support matrix and known gaps.

## Install

Install `uv` first:

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

macOS Homebrew:

```bash
brew install uv
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Install `unlimited-search`.

Because this repository is private, install commands need a GitHub token with repository read access in `GITHUB_TOKEN`.

macOS / Linux:

```bash
curl -fsSL \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.raw" \
  https://api.github.com/repos/flyingsquirrel0419/unlimited-search/contents/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "$h=@{Authorization='Bearer '+$env:GITHUB_TOKEN;Accept='application/vnd.github.raw'}; irm -Headers $h https://api.github.com/repos/flyingsquirrel0419/unlimited-search/contents/scripts/install.ps1 | iex"
```

Alternatively, with GitHub CLI:

```bash
gh repo clone flyingsquirrel0419/unlimited-search ~/.unlimited-search
cd ~/.unlimited-search
uv sync --no-dev
scripts/install.sh update
```

## Commands

```bash
unlimited-search serve
unlimited-search read https://example.com
unlimited-search read https://example.com --max-attempts 0
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
unlimited-search update
unlimited-search uninstall
unlimited-search help
```

Notes:

- `read` returns content, trace, verdict, and metadata.
- `diagnose` returns the compact trace without full content.
- `media` uses `yt-dlp --dump-json` and does not download media.
- `--max-attempts 0` skips the generic HTTP grid, which is useful for forcing content fallback smoke tests.

## MCP Config

macOS / Linux:

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

Windows PowerShell:

```json
{
  "mcpServers": {
    "unlimited-search": {
      "command": "powershell",
      "args": [
        "-ExecutionPolicy",
        "ByPass",
        "-File",
        "C:\\Users\\YOU\\.local\\bin\\unlimited-search.ps1",
        "serve"
      ]
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

# Full test suite
uv run pytest
```

## Project Docs

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
