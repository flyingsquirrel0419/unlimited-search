# unlimited-search

MCP server for reading public web pages through resilient public-only routes.

## Install

Install `uv` first.

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

Because this repository is private, install commands need a GitHub token with repository read access.

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
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
unlimited-search update
unlimited-search uninstall
unlimited-search help
```

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
uv run unlimited-search serve
uv run pytest
```

## Tools

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

Reads use public routes first, then a browser-like HTTP grid, then non-browser content fallbacks such as Jina Reader, RSS/Atom discovery, and metadata salvage.

## Project Docs

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
