# MCP Configuration

Use the PyPI-installed command when possible. It keeps the MCP client independent from a source checkout.

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

If the command is not found, confirm the package is installed and that Python's script directory is on `PATH`:

```bash
python -m pip install unlimited-search
unlimited-search help
```

## Local Development

```json
{
  "mcpServers": {
    "unlimited-search": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/unlimited-search",
        "run",
        "unlimited-search",
        "serve"
      ]
    }
  }
}
```

## Tool Behavior

The MCP server exposes:

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

`read_public_url` and `read_public_urls` return content, verdict, trace, and metadata. If direct access fails, results may include:

- `metadata.platform = "content-fallback"` with routes such as `jina-json`, `rss-discovery`, or `metadata-salvage`
- `metadata.platform = "archive-fallback"` with routes such as `wayback-available`, `wayback-latest`, `wayback-cdx`, or `archive-today`
- `metadata.fallback_verdict` to distinguish recovered content from direct strong reads

`diagnose_access` omits full content and is better for debugging blocked, challenged, or rate-limited URLs.
