# unlimited-search

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | 日本語 | [Español](README.es.md)

[![test](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml/badge.svg)](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

<p align="center"><strong>不可能はありません。公開されているなら、unlimited-search が読める経路を見つけます。</strong></p>

<p align="center">
  <img src="assets/hero.png" width="860" alt="unlimited-search が公開 URL を routes、HTTP、RSS、archives、media 経由で MCP と CLI 向けの構造化テキストに変換するヒーロー画像。">
</p>

`unlimited-search` は、通常の direct fetch だけでは不十分な公開 Web コンテンツを読むための Python CLI と MCP サーバーです。プラットフォーム別の公開 route、ブラウザ風 HTTP identity、content fallback、公開 archive fallback、メディアメタデータ抽出を 1 つのローカルツールにまとめます。

公開 URL から利用可能なテキストを必要とする agent や自動化向けに作られています。ログイン、paywall、CAPTCHA、プライベートネットワーク、アカウント制限、IP ban、アクセス制御を回避するためのものではありません。

## クイックスタート

前提条件: Python 3.12 以上。

```bash
python -m pip install unlimited-search
unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 800
```

このコマンドはページの `content`、`verdict`、リクエスト `metadata`、試行 `trace` を含む JSON を返します。

MCP クライアントでは、パッケージをインストールして stdio サーバーを登録します。

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

## 提供機能

| 機能 | 説明 |
| --- | --- |
| 公開 platform route | 汎用 fetch の前に、認証不要の公開 API、feed、metadata route を使います。 |
| ブラウザ風 fetch | 複数の TLS/browser identity、URL variant、referer strategy、response validation を試します。 |
| Content fallback | Jina Reader、RSS/Atom discovery、ページ内 metadata から公開テキストを復元します。 |
| Archive fallback | live read が失敗した場合、Wayback と archive.today/archive.ph の公開 snapshot に fallback します。 |
| メディア metadata | メディアをダウンロードせず、`yt-dlp --dump-json` で公開メディア metadata を抽出します。 |
| MCP tools | MCP クライアントに単一 URL 読み取り、batch 読み取り、診断、メディア抽出を提供します。 |

完全な対応表と既知の制限は [Platform coverage](PLATFORMS.md) を参照してください。

## インストール

PyPI からインストールします。

```bash
python -m pip install unlimited-search
```

更新:

```bash
python -m pip install --upgrade unlimited-search
```

削除:

```bash
python -m pip uninstall unlimited-search
```

## CLI 使い方

```bash
unlimited-search help
unlimited-search <command> [arguments]
```

コマンド:

```text
serve           MCP stdio サーバーを起動
read <url>      公開 URL を読む
diagnose <url>  完全な content なしでアクセス診断
media <url>     公開メディア metadata を抽出
help            この help を表示
```

よく使う例:

```bash
unlimited-search read https://example.com --max-content-chars 1000
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Fallback 中心の smoke test:

```bash
unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 500
unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 500
```

便利な flag:

| Flag | 対象コマンド | 目的 |
| --- | --- | --- |
| `--timeout SECONDS` | `read`, `diagnose`, `media` | request timeout を設定 |
| `--max-attempts N` | `read`, `diagnose` | 汎用 HTTP grid の試行回数を制限 |
| `--max-content-chars N` | `read` | 返す content サイズを制限 |
| `--no-public-routes` | `read`, `diagnose` | platform public route をスキップ |
| `--preferred-identity NAME` | `read`, `diagnose` | 指定したブラウザ風 identity を先に試す |
| `--success-selector CSS` | `read` | CSS selector の一致を成功シグナルとして扱う。複数指定可 |

## MCP ツール

MCP サーバーは stdio で動作します。

```bash
unlimited-search serve
```

利用可能なツール:

| ツール | 目的 |
| --- | --- |
| `read_public_url` | 1 つの公開 URL を読み、content、verdict、metadata、trace を返します。 |
| `read_public_urls` | 複数の公開 URL を 1 回の tool call で読みます。 |
| `diagnose_access` | 完全な content なしで compact diagnosis と attempt trace を返します。 |
| `extract_media` | メディアをダウンロードせずに `yt-dlp` で公開メディア metadata を抽出します。 |

設定例は [MCP configuration](docs/mcp-config.md) にあります。

## 読み取りの仕組み

<p align="center">
  <img src="assets/pipeline.png" width="860" alt="Public URL から platform routes、HTTP grid、content fallbacks、archive fallbacks、media metadata、clean public text へ進み、login、paywall、CAPTCHA は安全に停止する pipeline diagram。">
</p>

`read_public_url` は最も侵襲性の低い公開 route から試し、段階的に復元経路を広げます。

1. Reddit、X/Twitter、Bluesky、Hacker News、Google News、Stack Overflow、Wikipedia、GitHub、npm、PyPI、Wayback、Naver、Amazon、Google Scholar などの platform-specific public route
2. ブラウザ風 TLS identity、URL variant、referer strategy、response validation、選択的 HTTP/1.1 transport fallback を使う汎用 HTTP grid
3. 非ブラウザ content fallback
   - Jina Reader JSON content
   - Jina `external.alternate` からの RSS/Atom discovery
   - `/feed`、`/rss`、`/atom.xml` などの一般的な origin feed path
   - OGP、JSON-LD、Schema.org、Next.js payload metadata salvage
4. 公開 archive fallback
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshot
5. 既知の公開 media host に対する `yt-dlp` metadata extraction

Fallback 成功は `strong_ok` ではなく `weak_ok` または `suspect_ok` として報告されます。復元された content は不完全、古い、または metadata のみの場合があるためです。

## 安全境界

`unlimited-search` は公開コンテンツ reader です。対象が認証、支払い、CAPTCHA、プライベートネットワークアクセス、強い anti-abuse 回避を要求する場合、停止または失敗を報告します。

Reader はデフォルトで private、loopback、link-local、multicast、reserved、metadata-service target を拒否します。Redirect も fallback route の継続前に検査されます。

返された HTML、JSON、RSS、archive text、metadata は信頼できない content として扱ってください。

## 開発

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com --max-content-chars 300
uv run unlimited-search serve
uv run pytest
uv build
```

Route や fallback の動作を変更するときは live eval set を実行してください。

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

デフォルトの eval case は [scripts/eval_urls.yaml](scripts/eval_urls.yaml) にあります。NamuWiki、TikTok、Naver Search、Amazon、Google Scholar など難しいサイトは optional なので、リモート側のブロックや rate limit で全体の実行は失敗しません。

## プロジェクト文書

- [Platform coverage](PLATFORMS.md)
- [MCP configuration](docs/mcp-config.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)
