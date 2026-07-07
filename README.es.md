# unlimited-search

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | Español

Servidor MCP y CLI en Python para leer contenido web público mediante rutas públicas por plataforma, identidades HTTP similares a un navegador, fallbacks de contenido sin navegador, fallbacks de archivos públicos y extracción de metadatos de medios.

`unlimited-search` es una herramienta para contenido público. No está diseñada para eludir inicios de sesión, paywalls, CAPTCHA, redes privadas ni controles de acceso.

## Cómo Lee

`read_public_url` prueba estas capas en orden:

1. Rutas públicas de plataformas conocidas como Reddit, X/Twitter, Bluesky, Hacker News, Google News, Stack Overflow, Wikipedia, GitHub, npm, PyPI, Wayback y otras
2. Un grid HTTP genérico con identidades TLS similares a navegador, variantes de URL, estrategias de referer, validación de respuestas y fallback HTTP/1.1 con curl para ciertos fallos de transporte
3. Fallbacks de contenido sin navegador
   - Contenido JSON de Jina Reader
   - Descubrimiento RSS/Atom mediante Jina `external.alternate`
   - Rutas feed comunes como `/feed`, `/rss`, `/atom.xml`
   - Salvage de metadatos OGP, JSON-LD, Schema.org y payloads de Next.js
4. Fallbacks de archivos públicos
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - snapshots best-effort de archive.today/archive.ph
5. Extracción de metadatos con `yt-dlp` para hosts de medios públicos conocidos

Consulta [Platform coverage](PLATFORMS.md) para la matriz de soporte actual y las limitaciones conocidas.

## Instalación

Instala `uv` primero.

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

Instala `unlimited-search`.

Como este repositorio puede ser privado, los comandos de instalación necesitan un token de GitHub con acceso de lectura al repositorio en `GITHUB_TOKEN`.

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

También puedes usar GitHub CLI:

```bash
gh repo clone flyingsquirrel0419/unlimited-search ~/.unlimited-search
cd ~/.unlimited-search
uv sync --no-dev
scripts/install.sh update
```

## Comandos

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

Notas:

- `read` devuelve content, trace, verdict y metadata.
- `diagnose` devuelve un trace compacto sin el contenido completo.
- `media` usa `yt-dlp --dump-json` y no descarga medios.
- `--max-attempts 0` omite el grid HTTP genérico y sirve para forzar pruebas de content fallback.
- Los fallbacks exitosos se reportan intencionalmente como `weak_ok` o `suspect_ok`, no como `strong_ok`.

## Configuración MCP

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

## Desarrollo

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search serve
uv run pytest
```

## Herramientas MCP

- `read_public_url`
- `read_public_urls`
- `diagnose_access`
- `extract_media`

## Ejemplos de Verificación

```bash
uv run unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 300
uv run unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read https://xkcd.com/not-a-real-page --no-public-routes --max-attempts 0 --max-content-chars 300
uv run unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 300
uv run pytest
```

## Live Eval Set

Usa el live eval runner cuando cambies rutas o fallbacks y necesites evidencia antes/después con sitios reales.

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --group stable --group search
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

El conjunto predeterminado está en `scripts/eval_urls.yaml`. Sitios difíciles como NamuWiki, TikTok, Naver Search, Amazon y Google Scholar están marcados como opcionales, así que bloqueos remotos o rate limits no hacen fallar toda la ejecución.

## Documentos del Proyecto

- [Platform coverage](PLATFORMS.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Disclaimer](DISCLAIMER.md)
- [Privacy](PRIVACY.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [MCP configuration](docs/mcp-config.md)
