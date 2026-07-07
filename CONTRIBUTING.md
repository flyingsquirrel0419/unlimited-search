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

Run fallback smoke tests:

```bash
uv run unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
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
- document new public routes, fallbacks, or media behavior in `PLATFORMS.md`

## Public-Only Rule

This project reads public content through public routes. Contributions must not add logic intended to defeat authentication, paywalls, account restrictions, or private access controls.

## Testing Network Behavior

Network results can vary by IP, region, rate limits, and time. Prefer deterministic unit tests for validators, route selection, content fallback parsing, and transport fallback logic. Use live network checks only as smoke tests.
