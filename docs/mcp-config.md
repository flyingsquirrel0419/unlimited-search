# MCP Configuration

## macOS / Linux

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

## Windows PowerShell

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
