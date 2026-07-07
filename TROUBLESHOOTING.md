# Troubleshooting

## `unlimited-search` command not found

Add the install bin directory to `PATH`.

macOS / Linux default:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## `uv` command not found

Install `uv`.

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

## 403, 429, or Timeout

These can mean the target is rate-limiting, blocking automation, or requiring a browser challenge.

Try:

- wait before retrying
- lower request volume
- run `unlimited-search diagnose URL`
- check whether the page requires login or payment in a normal browser
- try a fallback-only smoke test with `--max-attempts 0`

```bash
unlimited-search read URL --no-public-routes --max-attempts 0 --max-content-chars 500
```

## Unexpected `content-fallback` result

`content-fallback` means the direct public-route or HTTP grid did not return clean content, but a non-browser fallback did.

Common routes:

- `jina-json`: Jina Reader returned page text.
- `rss-discovery`: an RSS/Atom feed was found through Jina or common feed paths.
- `metadata-salvage`: OGP, JSON-LD, Schema.org, or Next.js payload metadata was recovered from HTML.

This is usually acceptable for summaries, but it may not be equivalent to the full rendered page.

## RSS fallback returns unrelated latest posts

Feed fallback reads the site's feed, not necessarily the exact missing URL. This is useful when the goal is to recover public site content, but it can be too broad for exact-page reads. Check `metadata.source_url` to see which feed was used.

## `--max-attempts 0`

`--max-attempts 0` skips the generic HTTP grid. It still allows public routes unless `--no-public-routes` is also set.

Use both flags to test only content fallbacks:

```bash
unlimited-search read https://example.com --no-public-routes --max-attempts 0
```

## Google Scholar

Scholar is sensitive to repeated automated searches. The HTTP/1.1 fallback may work, then later return 403 or timeout after repeated requests. Wait before retrying.

## LinkedIn

LinkedIn may return status `999`. This is treated as blocked. Do not treat it as successful public content.

## TikTok

Some identities return a WAF shell such as `SlardarWAF` or `Please wait...`. `unlimited-search` treats those as challenges and continues to other identities when possible.

If `yt-dlp` reports an IP block for a public post, `unlimited-search` reports the failure. It does not bypass IP-based anti-abuse controls.

## Private repository install fails

The curl install commands require `GITHUB_TOKEN` with read access to `flyingsquirrel0419/unlimited-search`.

macOS / Linux:

```bash
echo "$GITHUB_TOKEN" | wc -c
```

Windows PowerShell:

```powershell
$env:GITHUB_TOKEN.Length
```

If token access is correct but install still fails, clone with GitHub CLI:

```bash
gh repo clone flyingsquirrel0419/unlimited-search ~/.unlimited-search
cd ~/.unlimited-search
uv sync --no-dev
scripts/install.sh update
```
