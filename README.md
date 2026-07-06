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

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/flyingsquirrel0419/unlimited-search/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/flyingsquirrel0419/unlimited-search/main/scripts/install.ps1 | iex"
```

For a private repository, raw GitHub install URLs require an authenticated environment. Clone-based install is the reliable private-repo path.

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

## Project Docs

- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
