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

## Publishing

PyPI publishing runs from GitHub Actions when a version tag is pushed:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Set `PYPI_API_TOKEN` in GitHub Actions secrets before pushing a release tag. For the first PyPI upload, use a token that can create the `unlimited-search` project.

The publish workflow checks PyPI before uploading and writes the release plan to the GitHub Actions summary:

- `deploy` when the PyPI project does not exist yet
- `update` when the PyPI project exists and the tagged version is new
- blocked when the exact version already exists, because PyPI does not allow replacing published distributions

The tag must match the version in `pyproject.toml`; for example, `version = "0.1.0"` must be released with tag `v0.1.0`.

```bash
python - <<'PY'
import tomllib
with open("pyproject.toml", "rb") as f:
    print(tomllib.load(f)["project"]["version"])
PY
```

## Public-Only Rule

This project reads public content through public routes. Contributions must not add logic intended to defeat authentication, paywalls, account restrictions, or private access controls.

## Testing Network Behavior

Network results can vary by IP, region, rate limits, and time. Prefer deterministic unit tests for validators, route selection, content fallback parsing, and transport fallback logic. Use live network checks only as smoke tests.
