# Platform Coverage

`unlimited-search` uses three layers:

1. Automatic public routes for platforms with stable unauthenticated APIs.
2. Generic browser-like HTTP fetching with TLS impersonation.
3. Non-browser content fallbacks through Jina Reader, RSS/Atom discovery, and metadata salvage.
4. `yt-dlp` metadata extraction for public media URLs.

This project does not bypass hard anti-abuse systems, login walls, paywalls, or IP bans.

## Automatic Public Routes

These source URLs are converted to public API or feed URLs before the generic fetch grid runs.

| Platform | Input examples | Route |
|---|---|---|
| X/Twitter | `twitter.com/{user}/status/{id}`, `x.com/{user}/status/{id}` | Syndication tweet-result, oEmbed |
| Reddit | `reddit.com/r/{subreddit}`, comments URLs | RSS first, JSON fallback |
| Bluesky | `bsky.app/profile/{actor}` | AT Protocol profile, author feed |
| Mastodon | known public instances such as `fosstodon.org/@user` | instance info, account lookup |
| Hacker News | `news.ycombinator.com`, `news.ycombinator.com/item?id=...` | Firebase top stories, Algolia item |
| Stack Overflow | question, tag, search, and questions pages | Stack Exchange API v2.3 |
| Lobste.rs | front page, tag, story URLs | JSON endpoints |
| V2EX | front page, node URLs | JSON endpoints |
| dev.to | front page, tag, user URLs | dev.to articles API |
| arXiv | `arxiv.org/abs/{id}`, search URLs | arXiv Atom API |
| DOI/CrossRef | `doi.org/{doi}` | CrossRef works API |
| Wikipedia | `{lang}.wikipedia.org/wiki/{title}` | REST page summary |
| OpenLibrary | ISBN, works, search URLs | OpenLibrary JSON APIs |
| GitHub | `github.com/{owner}/{repo}` releases/issues | GitHub REST API |
| npm | `npmjs.com/package/{package}` | npm registry latest |
| PyPI | `pypi.org/project/{package}` | PyPI JSON |
| Wayback | archived `web.archive.org/web/.../{url}` URLs | CDX API |
| Naver Blog | `blog.naver.com/{blogId}/{logNo}` | mobile blog post URL |
| Jina Reader fallback | Medium, Substack, Naver News, Naver Finance pages | `r.jina.ai` reader |

## Media Routes

Known public media hosts are routed through `yt-dlp --dump-json` from `read` and `media`.

| Platform | Notes |
|---|---|
| YouTube | metadata and captions when exposed by yt-dlp |
| Vimeo | metadata, subtitles when available |
| SoundCloud | metadata |
| Twitch | VOD/clip/live metadata when available; offline channels fail normally |
| TikTok | public posts only; current IP blocks are reported as failures |
| Dailymotion, Rumble | metadata through yt-dlp |
| Naver TV, Kakao, Chzzk, Soop/AfreecaTV | metadata through yt-dlp when public |

## Generic Fetch

Sites without a platform route still go through the normal fetch grid:

- browser-like identities from `curl_cffi`
- URL variants
- referer strategies
- HTTP/1.1 curl fallback for some transport failures
- response validation for challenges, rate limits, auth walls, JSON, and normal HTML

## Content Fallbacks

When public routes and the generic fetch grid do not produce a clean page, `unlimited-search` can still recover public content through:

- Jina Reader JSON output (`data.content`) for markdown-like page text.
- RSS/Atom discovery from Jina `external.alternate` and common origin feed paths.
- OGP, JSON-LD, Schema.org, and Next.js text payload metadata from the last usable HTML response.

## Known Gaps

These are intentionally not first-pass automatic parity:

- Browser challenge solving with Playwright.
- API-key, OAuth, or account-gated endpoints.
- X/Twitter keyword search orchestration through a web search engine.
- Archive.today and Google cache fallbacks.
- Hard anti-abuse bypasses such as TikTok IP bans or repeated 429 rate limits.
