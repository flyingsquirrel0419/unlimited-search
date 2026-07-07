# unlimited-search

[English](README.md) | 한국어 | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md)

공개 웹 콘텐츠를 안정적으로 읽기 위한 Python MCP 서버와 CLI입니다. 플랫폼별 공개 route, 브라우저형 HTTP identity, 비브라우저 content fallback, 공개 archive fallback, 미디어 메타데이터 추출을 제공합니다.

`unlimited-search`는 공개 콘텐츠 도구입니다. 로그인, paywall, CAPTCHA, 사설 네트워크, 접근 제어를 우회하기 위한 도구가 아닙니다.

## 읽기 방식

`read_public_url`은 다음 순서로 시도합니다.

1. Reddit, X/Twitter, Bluesky, Hacker News, Google News, Stack Overflow, Wikipedia, GitHub, npm, PyPI, Wayback 등 알려진 사이트의 공개 route
2. 브라우저형 TLS identity, URL 변형, referer 전략, 응답 검증, 선택적 HTTP/1.1 curl fallback을 사용하는 일반 HTTP grid
3. 비브라우저 content fallback
   - Jina Reader JSON content
   - Jina `external.alternate` 기반 RSS/Atom discovery
   - `/feed`, `/rss`, `/atom.xml` 같은 origin feed 후보
   - OGP, JSON-LD, Schema.org, Next.js payload metadata salvage
4. 공개 archive fallback
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshot
5. 공개 미디어 host에 대한 `yt-dlp` metadata extraction

현재 지원 범위와 알려진 한계는 [Platform coverage](PLATFORMS.md)를 참고하세요.

## 설치

먼저 `uv`를 설치합니다.

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

`unlimited-search`를 설치합니다.

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/flyingsquirrel0419/unlimited-search/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/flyingsquirrel0419/unlimited-search/main/scripts/install.ps1 | iex"
```

## 명령어

```bash
unlimited-search serve
unlimited-search read https://example.com
unlimited-search read https://example.com --max-attempts 0
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
unlimited-search update
unlimited-search uninstall
unlimited-search help
```

참고:

- `read`는 content, trace, verdict, metadata를 반환합니다.
- `diagnose`는 전체 content 없이 compact trace를 반환합니다.
- `media`는 `yt-dlp --dump-json`을 사용하며 미디어를 다운로드하지 않습니다.
- `--max-attempts 0`은 일반 HTTP grid를 건너뛰므로 content fallback smoke test에 유용합니다.
- fallback 성공은 의도적으로 `strong_ok`가 아니라 `weak_ok` 또는 `suspect_ok`로 표시됩니다.

## MCP 설정

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

## 개발

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search serve
uv run pytest
```

## MCP 도구

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

## 검증 예시

```bash
uv run unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 300
uv run unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 300
uv run pytest
```

## Live Eval Set

route나 fallback을 바꿀 때 실제 사이트 기준 before/after 근거가 필요하면 live eval runner를 사용하세요.

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --group stable --group search
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

기본 eval set은 `scripts/eval_urls.yaml`에 있습니다. NamuWiki, TikTok, Naver Search, Amazon, Google Scholar처럼 어려운 사이트는 optional로 표시되어 원격 차단이나 rate limit이 발생해도 전체 실행을 실패시키지 않습니다.

## 프로젝트 문서

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
