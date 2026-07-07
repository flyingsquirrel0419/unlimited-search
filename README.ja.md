# unlimited-search

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | 日本語 | [Español](README.es.md)

公開 Web コンテンツを読むための Python MCP サーバーと CLI です。プラットフォーム別の公開 route、ブラウザ風 HTTP identity、非ブラウザ content fallback、公開 archive fallback、メディアメタデータ抽出を提供します。

`unlimited-search` は公開コンテンツ用のツールです。ログイン、paywall、CAPTCHA、プライベートネットワーク、アクセス制御を回避するためのものではありません。

## 読み取りの仕組み

`read_public_url` は次の順序で試行します。

1. Reddit、X/Twitter、Bluesky、Hacker News、Google News、Stack Overflow、Wikipedia、GitHub、npm、PyPI、Wayback など既知サイトの公開 route
2. ブラウザ風 TLS identity、URL variant、referer strategy、response validation、一部 transport failure 用の HTTP/1.1 curl fallback を使う汎用 HTTP grid
3. 非ブラウザ content fallback
   - Jina Reader JSON content
   - Jina `external.alternate` からの RSS/Atom discovery
   - `/feed`、`/rss`、`/atom.xml` などの origin feed 候補
   - OGP、JSON-LD、Schema.org、Next.js payload metadata salvage
4. 公開 archive fallback
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshot
5. 既知の公開メディア host に対する `yt-dlp` metadata extraction

現在の対応状況と既知の制限は [Platform coverage](PLATFORMS.md) を参照してください。

## インストール

まず `uv` をインストールします。

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

`unlimited-search` をインストールします。

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/flyingsquirrel0419/unlimited-search/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/flyingsquirrel0419/unlimited-search/main/scripts/install.ps1 | iex"
```

## コマンド

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

メモ:

- `read` は content、trace、verdict、metadata を返します。
- `diagnose` は完全な content を含まない compact trace を返します。
- `media` は `yt-dlp --dump-json` を使い、メディアをダウンロードしません。
- `--max-attempts 0` は汎用 HTTP grid をスキップするため、content fallback の smoke test に便利です。
- fallback の成功は意図的に `strong_ok` ではなく `weak_ok` または `suspect_ok` として報告されます。

## MCP 設定

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

## 開発

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search serve
uv run pytest
```

## MCP ツール

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

## 検証例

```bash
uv run unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 300
uv run unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 300
uv run pytest
```

## Live Eval Set

route や fallback を変更したとき、実サイトで before/after の証拠を取りたい場合は live eval runner を使います。

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --group stable --group search
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

デフォルトの eval set は `scripts/eval_urls.yaml` にあります。NamuWiki、TikTok、Naver Search、Amazon、Google Scholar など難しいサイトは optional として扱われるため、リモート側のブロックや rate limit で全体の実行が失敗することはありません。

## プロジェクト文書

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
