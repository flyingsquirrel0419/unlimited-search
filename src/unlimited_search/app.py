from __future__ import annotations

import sys

from . import cli, server


def main(argv: list[str] | None = None) -> int | None:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "help"

    if command == "serve":
        server.main()
        return None
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
