from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .safety import classify_url


@dataclass(slots=True)
class MediaResult:
    ok: bool
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "url": self.url,
            "metadata": self.metadata,
            "error": self.error,
        }


def extract_media_metadata(url: str, *, timeout: int = 90) -> MediaResult:
    ok, reason = classify_url(url)
    if not ok:
        return MediaResult(False, url, error=f"unsafe_url:{reason}")

    try:
        proc = subprocess.run(
            ["yt-dlp", "--dump-json", "--skip-download", "--no-warnings", url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return MediaResult(False, url, error="yt-dlp_not_installed")
    except subprocess.TimeoutExpired:
        return MediaResult(False, url, error=f"yt-dlp_timeout:{timeout}s")
    except Exception as exc:
        return MediaResult(False, url, error=f"{type(exc).__name__}:{str(exc)[:240]}")

    if proc.returncode != 0:
        return MediaResult(False, url, error=(proc.stderr or "yt-dlp_failed")[:500])
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return MediaResult(False, url, error=f"invalid_yt_dlp_json:{exc}")

    keys = (
        "id",
        "title",
        "description",
        "duration",
        "channel",
        "uploader",
        "upload_date",
        "view_count",
        "like_count",
        "webpage_url",
        "thumbnail",
        "ext",
        "extractor",
    )
    metadata = {key: raw.get(key) for key in keys if key in raw}
    subtitles = raw.get("subtitles") or {}
    automatic_captions = raw.get("automatic_captions") or {}
    if subtitles:
        metadata["subtitle_languages"] = sorted(subtitles)
    if automatic_captions:
        metadata["automatic_caption_languages"] = sorted(automatic_captions)
    return MediaResult(True, url, metadata=metadata)
