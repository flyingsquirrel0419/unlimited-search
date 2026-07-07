# Troubleshooting

## `unlimited-search` command not found

Confirm the package is installed and that Python's script directory is on `PATH`.

```bash
python -m pip install unlimited-search
unlimited-search help
```

## Package install fails

Upgrade packaging tools, then retry.

```bash
python -m pip install --upgrade pip
python -m pip install unlimited-search
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

## Unexpected `archive-fallback` result

`archive-fallback` means the live URL and content fallbacks failed, but a public archive snapshot was available.

Common routes:

- `wayback-available`: Wayback Available API returned a closest snapshot.
- `wayback-latest`: Wayback resolved a direct latest snapshot.
- `wayback-cdx`: Wayback CDX returned the latest HTTP 200 snapshot.
- `archive-today`: archive.today/archive.ph mirror returned a readable snapshot.

Archive snapshots can be stale, incomplete, or different from the live page. Check `metadata.source_url` before treating the content as current.

## `--max-attempts 0`

`--max-attempts 0` skips the generic HTTP grid. It still allows public routes unless `--no-public-routes` is also set.

Use both flags to test only content fallbacks:

```bash
unlimited-search read https://example.com --no-public-routes --max-attempts 0
```

Archive fallback is most useful after the original URL is confirmed missing or blocked. Use at least one generic attempt when testing archive recovery:

```bash
unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1
```

## Google Scholar

Scholar is sensitive to repeated automated searches. The HTTP/1.1 fallback may work, then later return 403 or timeout after repeated requests. Wait before retrying.

## LinkedIn

LinkedIn may return status `999`. This is treated as blocked. Do not treat it as successful public content.

## TikTok

Some identities return a WAF shell such as `SlardarWAF` or `Please wait...`. `unlimited-search` treats those as challenges and continues to other identities when possible.

If `yt-dlp` reports an IP block for a public post, `unlimited-search` reports the failure. It does not bypass IP-based anti-abuse controls.
