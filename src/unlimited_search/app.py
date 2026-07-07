from __future__ import annotations

import os
from pathlib import Path
import sys
import webbrowser

from . import cli, server

STAR_URL = "https://github.com/flyingsquirrel0419/unlimited-search"
STAR_PROMPT_DISABLE_ENV = "UNLIMITED_SEARCH_NO_STAR_PROMPT"
STAR_PROMPT_STATE_ENV = "UNLIMITED_SEARCH_STATE_DIR"


def _state_dir() -> Path:
    override = os.environ.get(STAR_PROMPT_STATE_ENV)
    if override:
        return Path(override)
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home) / "unlimited-search"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local_app_data:
            return Path(local_app_data) / "unlimited-search"
    return Path.home() / ".local" / "state" / "unlimited-search"


def _star_prompt_marker() -> Path:
    return _state_dir() / "star_prompt_seen"


def _mark_star_prompt_seen() -> None:
    try:
        marker = _star_prompt_marker()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("seen\n", encoding="utf-8")
    except OSError as exc:
        print(f"warning: could not save star prompt state: {exc}", file=sys.stderr)


def _should_prompt_for_star(command: str) -> bool:
    if command not in {"help", "-h", "--help", "read", "diagnose", "media"}:
        return False
    if os.environ.get(STAR_PROMPT_DISABLE_ENV):
        return False
    if _star_prompt_marker().exists():
        return False
    return sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()


def _maybe_prompt_for_star(command: str) -> None:
    if not _should_prompt_for_star(command):
        return

    try:
        print("Star unlimited-search on GitHub? [y/N]: ", end="", file=sys.stderr, flush=True)
        answer = sys.stdin.readline()
        if answer == "":
            raise EOFError
        answer = answer.strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("", file=sys.stderr)
        _mark_star_prompt_seen()
        return

    _mark_star_prompt_seen()
    if answer not in {"y", "yes"}:
        return

    try:
        opened = webbrowser.open(STAR_URL, new=2)
    except Exception as exc:  # pragma: no cover - depends on host browser setup
        print(f"warning: could not open browser for GitHub star page: {exc}", file=sys.stderr)
        return
    if not opened:
        print("warning: could not open browser for GitHub star page; skipping.", file=sys.stderr)


def main(argv: list[str] | None = None) -> int | None:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "help"

    if command == "serve":
        server.main()
        return None
    _maybe_prompt_for_star(command)
    if command in {"read", "diagnose", "media"}:
        return cli.main(args)
    if command in {"help", "-h", "--help"}:
        print(
            "unlimited-search\n\n"
            "Usage:\n"
            "  unlimited-search serve\n"
            "  unlimited-search read URL\n"
            "  unlimited-search diagnose URL\n"
            "  unlimited-search media URL\n"
        )
        return 0
    print(f"unknown command: {command}", file=sys.stderr)
    print("run: unlimited-search help", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
