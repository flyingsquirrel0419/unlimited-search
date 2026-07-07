# unlimited-search

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | Español

[![test](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml/badge.svg)](https://github.com/flyingsquirrel0419/unlimited-search/actions/workflows/test.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

<p align="center"><strong>De páginas públicas a señales utilizables.</strong></p>

<p align="center">
  <img src="assets/hero.png" width="860" alt="Imagen hero de unlimited-search mostrando URLs públicas que pasan por routes, HTTP, RSS, archives y media para convertirse en texto estructurado para MCP y CLI.">
</p>

`unlimited-search` es un CLI de Python y servidor MCP para leer contenido web público cuando un fetch directo normal no es suficiente. Combina rutas públicas por plataforma, identidades HTTP similares a navegador, fallbacks de contenido, fallbacks de archivos públicos y extracción de metadatos de medios en una herramienta local.

Está diseñado para agentes y automatización que necesitan texto utilizable desde URLs públicas. No está pensado para eludir inicios de sesión, paywalls, CAPTCHA, redes privadas, restricciones de cuenta, bloqueos por IP ni controles de acceso.

## Inicio Rápido

Requisito: Python 3.12 o superior.

```bash
python -m pip install unlimited-search
unlimited-search read https://en.wikipedia.org/wiki/OpenAI --max-content-chars 800
```

El comando devuelve JSON con `content`, `verdict`, `metadata` de la solicitud y `trace` de intentos.

Para clientes MCP, instala el paquete y registra el servidor stdio:

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

## Qué Ofrece

| Capacidad | Qué hace |
| --- | --- |
| Rutas públicas de plataformas | Usa APIs, feeds o rutas de metadata públicas sin autenticación antes del fetch genérico. |
| Fetch similar a navegador | Prueba varias identidades TLS/browser, variantes de URL, estrategias de referer y validación de respuestas. |
| Fallbacks de contenido | Recupera texto público mediante Jina Reader, RSS/Atom discovery y metadata embebida en la página. |
| Fallbacks de archivo | Recurre a snapshots públicos de Wayback y archive.today/archive.ph cuando falla la lectura live. |
| Metadata de medios | Usa `yt-dlp --dump-json` para URLs de medios públicos sin descargar el medio. |
| Herramientas MCP | Expone lectura de una URL, lectura batch, diagnóstico y extracción de medios a clientes MCP. |

Consulta [Platform coverage](PLATFORMS.md) para la matriz completa de soporte y limitaciones conocidas.

## Instalación

Instala desde PyPI:

```bash
python -m pip install unlimited-search
```

Actualiza:

```bash
python -m pip install --upgrade unlimited-search
```

Elimina:

```bash
python -m pip uninstall unlimited-search
```

## Uso CLI

```bash
unlimited-search help
unlimited-search <command> [arguments]
```

Comandos:

```text
serve           Inicia el servidor MCP stdio
read <url>      Lee una URL pública
diagnose <url>  Diagnostica acceso sin contenido completo
media <url>     Extrae metadata de medios públicos
help            Muestra esta ayuda
```

Ejemplos comunes:

```bash
unlimited-search read https://example.com --max-content-chars 1000
unlimited-search diagnose https://example.com
unlimited-search media https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Smoke tests centrados en fallbacks:

```bash
unlimited-search read https://example.com --no-public-routes --max-attempts 0 --max-content-chars 500
unlimited-search read http://www.whitehouse.gov/1600/presidents/barackobama --no-public-routes --max-attempts 1 --max-content-chars 500
```

Flags útiles:

| Flag | Aplica a | Propósito |
| --- | --- | --- |
| `--timeout SECONDS` | `read`, `diagnose`, `media` | Define el timeout de la solicitud. |
| `--max-attempts N` | `read`, `diagnose` | Limita los intentos del HTTP grid genérico. |
| `--max-content-chars N` | `read` | Limita el tamaño del contenido devuelto. |
| `--no-public-routes` | `read`, `diagnose` | Omite las rutas públicas de plataforma. |
| `--preferred-identity NAME` | `read`, `diagnose` | Intenta primero una identidad similar a navegador específica. |
| `--success-selector CSS` | `read` | Trata selectores CSS coincidentes como señales de éxito. Se puede repetir. |

## Herramientas MCP

El servidor MCP corre sobre stdio:

```bash
unlimited-search serve
```

Herramientas disponibles:

| Herramienta | Propósito |
| --- | --- |
| `read_public_url` | Lee una URL pública y devuelve content, verdict, metadata y trace. |
| `read_public_urls` | Lee varias URLs públicas en una sola tool call. |
| `diagnose_access` | Devuelve un diagnóstico compacto y trace de intentos sin contenido completo. |
| `extract_media` | Extrae metadata de medios públicos mediante `yt-dlp` sin descargar medios. |

Hay más ejemplos de configuración en [MCP configuration](docs/mcp-config.md).

## Cómo Lee

<p align="center">
  <img src="assets/pipeline.png" width="860" alt="Diagrama de pipeline: Public URL a platform routes, HTTP grid, content fallbacks, archive fallbacks, media metadata y clean public text, con login, paywall o CAPTCHA deteniéndose de forma segura.">
</p>

`read_public_url` prueba primero las rutas públicas menos invasivas y luego amplía progresivamente las rutas de recuperación:

1. Rutas públicas específicas para plataformas como Reddit, X/Twitter, Bluesky, Hacker News, Google News, Stack Overflow, Wikipedia, GitHub, npm, PyPI, Wayback, Naver, Amazon y Google Scholar.
2. Un HTTP grid genérico con identidades TLS similares a navegador, variantes de URL, estrategias de referer, validación de respuesta y fallback de transporte HTTP/1.1 seleccionado.
3. Fallbacks de contenido sin navegador:
   - Jina Reader JSON content
   - RSS/Atom discovery mediante Jina `external.alternate`
   - rutas origin feed comunes como `/feed`, `/rss` y `/atom.xml`
   - salvage de metadata OGP, JSON-LD, Schema.org y payloads de Next.js
4. Fallbacks de archivo público:
   - Wayback Available API
   - Wayback latest/direct snapshot
   - Wayback CDX latest 200 snapshot
   - snapshots best-effort de archive.today/archive.ph
5. Extracción de metadata con `yt-dlp` para hosts de medios públicos conocidos.

Los fallbacks exitosos se reportan como `weak_ok` o `suspect_ok`, no como `strong_ok`, porque el contenido recuperado puede estar incompleto, obsoleto o contener solo metadata.

## Límites de Seguridad

`unlimited-search` es un lector de contenido público. Debe detenerse o reportar fallo cuando un objetivo requiere autenticación, pago, CAPTCHA, acceso a red privada o elusión fuerte de sistemas anti-abuso.

El lector rechaza por defecto objetivos private, loopback, link-local, multicast, reserved y metadata-service. Los redirects se validan antes de permitir que continúen las rutas fallback.

El HTML, JSON, RSS, texto de archivo y metadata devueltos deben tratarse como contenido no confiable.

## Desarrollo

```bash
uv sync --extra dev
uv run unlimited-search read https://example.com --max-content-chars 300
uv run unlimited-search serve
uv run pytest
uv build
```

Ejecuta el live eval set cuando cambies rutas o comportamiento de fallback:

```bash
uv run python scripts/run_eval.py --list
uv run python scripts/run_eval.py
uv run python scripts/run_eval.py --markdown eval-results/report.md --csv eval-results/report.csv
uv run python scripts/run_eval.py --baseline eval-results/eval-20260707T000000Z.jsonl --fail-on-regression
```

Los casos eval predeterminados están en [scripts/eval_urls.yaml](scripts/eval_urls.yaml). Sitios difíciles como NamuWiki, TikTok, Naver Search, Amazon y Google Scholar son opcionales, así que bloqueos remotos o rate limits no hacen fallar toda la ejecución.

## Documentos del Proyecto

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
