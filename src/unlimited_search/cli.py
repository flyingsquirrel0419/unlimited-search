from __future__ import annotations

import argparse
import json
import sys

from .engine.media import extract_media_metadata
from .engine.reader import UnlimitedSearchReader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="unlimited-search-read")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("url")
    read_parser.add_argument("--timeout", type=int, default=25)
    read_parser.add_argument("--max-attempts", type=int, default=12)
    read_parser.add_argument("--max-content-chars", type=int, default=120000)
    read_parser.add_argument("--no-public-routes", action="store_true")
    read_parser.add_argument("--preferred-identity")
    read_parser.add_argument("--success-selector", action="append", dest="success_selectors")

    diagnose_parser = subparsers.add_parser("diagnose")
    diagnose_parser.add_argument("url")
    diagnose_parser.add_argument("--timeout", type=int, default=25)
    diagnose_parser.add_argument("--max-attempts", type=int, default=12)
    diagnose_parser.add_argument("--no-public-routes", action="store_true")
    diagnose_parser.add_argument("--preferred-identity")

    media_parser = subparsers.add_parser("media")
    media_parser.add_argument("url")
    media_parser.add_argument("--timeout", type=int, default=90)

    args = parser.parse_args(argv)

    if args.command == "media":
        payload = extract_media_metadata(args.url, timeout=args.timeout).to_dict()
    else:
        reader = UnlimitedSearchReader()
        if args.command == "read":
            payload = reader.read_public_url(
                args.url,
                timeout=args.timeout,
                max_attempts=args.max_attempts,
                max_content_chars=args.max_content_chars,
                enable_public_routes=not args.no_public_routes,
                preferred_identity=args.preferred_identity,
                success_selectors=args.success_selectors,
            ).to_dict()
        elif args.command == "diagnose":
            payload = reader.diagnose_access(
                args.url,
                timeout=args.timeout,
                max_attempts=args.max_attempts,
                max_content_chars=2000,
                enable_public_routes=not args.no_public_routes,
                preferred_identity=args.preferred_identity,
            ).to_dict()
            payload["content"] = ""
        else:
            parser.error(f"unknown command: {args.command}")
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
