# Contributing

Thanks for contributing to `unlimited-search`.

## Development Setup

```bash
uv sync --extra dev
uv run pytest
```

Run a local smoke test:

```bash
uv run unlimited-search read https://example.com --max-attempts 1 --max-content-chars 300
```

Run the MCP server:

```bash
uv run unlimited-search serve
```

## Pull Requests

Before opening a PR:

- keep changes focused
- add or update tests for behavior changes
- run `uv run pytest`
- do not include unrelated formatting churn
- do not add site-specific bypass logic without a clear public-content reason

## Public-Only Rule

This project reads public content through public routes. Contributions must not add logic intended to defeat authentication, paywalls, account restrictions, or private access controls.

## Testing Network Behavior

Network results can vary by IP, region, rate limits, and time. Prefer deterministic unit tests for validators, route selection, and transport fallback logic. Use live network checks only as smoke tests.
