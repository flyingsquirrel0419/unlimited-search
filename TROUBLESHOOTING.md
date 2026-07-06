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

## Google Scholar

Scholar is sensitive to repeated automated searches. The HTTP/1.1 fallback may work, then later return 403 or timeout after repeated requests. Wait before retrying.

## LinkedIn

LinkedIn may return status `999`. This is treated as blocked. Do not treat it as successful public content.

## TikTok

Some identities return a WAF shell such as `SlardarWAF` or `Please wait...`. `unlimited-search` treats those as challenges and continues to other identities when possible.
