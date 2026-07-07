# unlimited-search

[English](README.md) | [한국어](README.ko.md) | 中文 | [日本語](README.ja.md) | [Español](README.es.md)

用于读取公开网页内容的 Python MCP 服务器和 CLI。它支持平台公开路由、类似浏览器的 HTTP identity、非浏览器内容 fallback、公开 archive fallback，以及媒体元数据提取。

`unlimited-search` 是公开内容工具。它不是用于绕过登录、付费墙、CAPTCHA、私有网络或访问控制的工具。

## 工作方式

`read_public_url` 会按以下层级尝试读取：

1. 已知站点的公开路由，例如 Reddit、X/Twitter、Bluesky、Hacker News、Google News、Stack Overflow、Wikipedia、GitHub、npm、PyPI、Wayback 等
2. 通用 HTTP grid，包括类似浏览器的 TLS identity、URL 变体、referer 策略、响应验证，以及针对部分传输失败的 HTTP/1.1 curl fallback
3. 非浏览器内容 fallback
   - Jina Reader JSON content
   - 通过 Jina `external.alternate` 发现 RSS/Atom
   - `/feed`、`/rss`、`/atom.xml` 等常见 origin feed
   - OGP、JSON-LD、Schema.org、Next.js payload metadata salvage
4. 公开 archive fallback
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshot
5. 对已知公开媒体 host 使用 `yt-dlp` 提取元数据

当前平台覆盖范围和已知限制见 [Platform coverage](PLATFORMS.md)。

## 安装

先安装 `uv`。

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

安装 `unlimited-search`。

如果此仓库是 private，需要在 `GITHUB_TOKEN` 中提供具有仓库读取权限的 GitHub token。

macOS / Linux:

```bash
curl -fsSL \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.raw" \
  https://api.github.com/repos/flyingsquirrel0419/unlimited-search/contents/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "$h=@{Authorization='Bearer '+$env:GITHUB_TOKEN;Accept='application/vnd.github.raw'}; irm -Headers $h https://api.github.com/repos/flyingsquirrel0419/unlimited-search/contents/scripts/install.ps1 | iex"
```

也可以使用 GitHub CLI。

```bash
gh repo clone flyingsquirrel0419/unlimited-search ~/.unlimited-search
cd ~/.unlimited-search
uv sync --no-dev
scripts/install.sh update
```

## 命令

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

说明：

- `read` 返回 content、trace、verdict 和 metadata。
- `diagnose` 返回不包含完整 content 的 compact trace。
- `media` 使用 `yt-dlp --dump-json`，不会下载媒体文件。
- `--max-attempts 0` 会跳过通用 HTTP grid，适合强制测试 content fallback。
- fallback 成功会有意标记为 `weak_ok` 或 `suspect_ok`，而不是 `strong_ok`。

## MCP 配置

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

## 开发

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search serve
uv run pytest
```

## MCP 工具

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

## 验证示例

```bash
uv run unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 300
uv run unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 300
uv run pytest
```

## Live Eval Set

当你修改 route 或 fallback，并希望用真实站点做 before/after 证据时，可以使用 live eval runner。

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --group stable --group search
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

默认 eval set 位于 `scripts/eval_urls.yaml`。NamuWiki、TikTok、Naver Search、Amazon、Google Scholar 等困难站点被标记为 optional，因此远端阻断或 rate limit 不会导致整个运行失败。

## 项目文档

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
