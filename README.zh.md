# unlimited-search

[English](README.md) | [한국어](README.ko.md) | 中文 | [日本語](README.ja.md) | [Español](README.es.md)

[![test](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml/badge.svg)](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

<p align="center"><strong>将公开 URL 转换为可直接供 agent 使用的上下文。</strong></p>

<p align="center">
  <img src="assets/hero.png" width="860" alt="unlimited-search hero，展示公开 URL 通过 routes、HTTP、RSS、archives 和 media 转换为适用于 MCP 与 CLI 的结构化文本。">
</p>

`unlimited-search` 是一个 Python CLI 和 MCP 服务器，用于在普通 direct fetch 不够时读取公开网页内容。它把平台公开路由、类似浏览器的 HTTP identity、内容 fallback、公开 archive fallback 和媒体元数据提取整合为一个本地工具。

它面向需要从公开 URL 获取可用文本的 agent 和自动化流程。它不用于绕过登录、付费墙、CAPTCHA、私有网络、账号限制、IP ban 或访问控制。

## 快速开始

前提条件：Python 3.12 或更高版本。

```bash
python -m pip install unlimited-search
unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 800
```

该命令会返回 JSON，其中包含页面 `content`、`verdict`、请求 `metadata` 和尝试 `trace`。

对于 MCP 客户端，安装包后注册 stdio 服务器：

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

## 提供能力

| 能力 | 说明 |
| --- | --- |
| 公开平台路由 | 在通用 fetch 前使用无需认证的公开 API、feed 或 metadata route。 |
| 类浏览器 fetch | 尝试多种 TLS/browser identity、URL 变体、referer 策略和响应验证。 |
| 内容 fallback | 通过 Jina Reader、RSS/Atom discovery 和页面内 metadata 恢复公开文本。 |
| Archive fallback | live read 失败时回退到 Wayback 和 archive.today/archive.ph 公开 snapshot。 |
| 媒体 metadata | 使用 `yt-dlp --dump-json` 提取公开媒体 metadata，不下载媒体。 |
| MCP 工具 | 向 MCP 客户端暴露单 URL 读取、批量读取、诊断和媒体提取工具。 |

完整支持矩阵和已知限制见 [Platform coverage](PLATFORMS.md)。

## 安装

从 PyPI 安装：

```bash
python -m pip install unlimited-search
```

更新：

```bash
python -m pip install --upgrade unlimited-search
```

卸载：

```bash
python -m pip uninstall unlimited-search
```

## CLI 用法

```bash
unlimited-search help
unlimited-search <command> [arguments]
```

命令：

```text
serve           启动 MCP stdio 服务器
read <url>      读取公开 URL
diagnose <url>  诊断访问情况，不返回完整 content
media <url>     提取公开媒体 metadata
help            显示此帮助
```

常用示例：

```bash
unlimited-search read https://example.com --max-content-chars 1000
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

面向 fallback 的 smoke test：

```bash
unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 500
unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 500
```

常用 flag：

| Flag | 适用命令 | 目的 |
| --- | --- | --- |
| `--timeout SECONDS` | `read`, `diagnose`, `media` | 设置请求 timeout。 |
| `--max-attempts N` | `read`, `diagnose` | 限制通用 HTTP grid 尝试次数。 |
| `--max-content-chars N` | `read` | 限制返回 content 大小。 |
| `--no-public-routes` | `read`, `diagnose` | 跳过平台公开路由。 |
| `--preferred-identity NAME` | `read`, `diagnose` | 优先尝试指定的类浏览器 identity。 |
| `--success-selector CSS` | `read` | 将匹配的 CSS selector 作为成功信号。可重复使用。 |

## MCP 工具

MCP 服务器通过 stdio 运行：

```bash
unlimited-search serve
```

可用工具：

| 工具 | 目的 |
| --- | --- |
| `read_public_url` | 读取一个公开 URL，并返回 content、verdict、metadata 和 trace。 |
| `read_public_urls` | 在一次 tool call 中读取多个公开 URL。 |
| `diagnose_access` | 返回 compact diagnosis 和 attempt trace，不包含完整 content。 |
| `extract_media` | 通过 `yt-dlp` 提取公开媒体 metadata，不下载媒体。 |

更多配置示例见 [MCP configuration](docs/mcp-config.md)。

## 读取方式

<p align="center">
  <img src="assets/pipeline.png" width="860" alt="Pipeline diagram：Public URL 依次经过 platform routes、HTTP grid、content fallbacks、archive fallbacks、media metadata 到 clean public text；login、paywall 或 CAPTCHA 会安全停止。">
</p>

`read_public_url` 会先尝试最小侵入的公开 route，然后逐步扩大恢复路径：

1. 面向 Reddit、X/Twitter、Bluesky、Hacker News、Google News、Stack Overflow、Wikipedia、GitHub、npm、PyPI、Wayback、Naver、Amazon、Google Scholar 等平台的公开 route
2. 通用 HTTP grid：类浏览器 TLS identity、URL 变体、referer 策略、响应验证，以及选定的 HTTP/1.1 transport fallback
3. 非浏览器内容 fallback
   - Jina Reader JSON content
   - 通过 Jina `external.alternate` 发现 RSS/Atom
   - `/feed`、`/rss`、`/atom.xml` 等常见 origin feed path
   - OGP、JSON-LD、Schema.org、Next.js payload metadata salvage
4. 公开 archive fallback
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - archive.today/archive.ph best-effort snapshot
5. 面向已知公开媒体 host 的 `yt-dlp` metadata extraction

Fallback 成功会报告为 `weak_ok` 或 `suspect_ok`，而不是 `strong_ok`，因为恢复内容可能不完整、过期或只有 metadata。

## 安全边界

`unlimited-search` 是公开内容 reader。当目标要求认证、付费、CAPTCHA、私有网络访问或强 anti-abuse 绕过时，它应该停止或报告失败。

Reader 默认拒绝 private、loopback、link-local、multicast、reserved 和 metadata-service 目标。Fallback route 继续前也会检查 redirect。

返回的 HTML、JSON、RSS、archive text 和 metadata 都应视为不可信内容。

## 开发

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com --max-content-chars 300
uv run unlimited-search serve
uv run pytest
uv build
```

修改 route 或 fallback 行为时，运行 live eval set：

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

默认 eval case 位于 [scripts/eval_urls.yaml](scripts/eval_urls.yaml)。NamuWiki、TikTok、Naver Search、Amazon、Google Scholar 等困难站点是 optional，因此远端阻断或 rate limit 不会导致整个运行失败。

## 项目文档

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
