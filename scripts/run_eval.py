#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import yaml

from unlimited_search.engine.media import extract_media_metadata
from unlimited_search.engine.reader import UnlimitedSearchReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "scripts" / "eval_urls.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "eval-results"

ReaderFactory = Callable[[], UnlimitedSearchReader]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cases = load_cases(args.cases)
    cases = select_cases(cases, ids=args.id, groups=args.group, limit=args.limit)
    if args.list:
        for case in cases:
            print(f"{case['id']}\t{case.get('group', '')}\t{case['url']}")
        return 0

    baseline = load_jsonl_by_id(args.baseline) if args.baseline else {}
    output_path = output_path_for(args.output)
    rows = run_cases(cases, baseline=baseline, fail_on_regression=args.fail_on_regression)
    write_jsonl(rows, output_path)
    if args.markdown:
        write_markdown(rows, Path(args.markdown))
    if args.csv:
        write_csv(rows, Path(args.csv))
    print_summary(rows, output_path)
    return 1 if any(row["status"] in {"fail", "regression"} for row in rows) else 0


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    defaults = data.get("defaults") or {}
    cases: list[dict[str, Any]] = []
    for raw_case in data.get("cases") or []:
        raw = raw_case or {}
        case = {**defaults, **raw}
        case["expect"] = {**(defaults.get("expect") or {}), **(raw.get("expect") or {})}
        if not case.get("id") or not case.get("url"):
            raise ValueError("each eval case needs id and url")
        cases.append(case)
    return cases


def select_cases(
    cases: list[dict[str, Any]],
    *,
    ids: list[str] | None = None,
    groups: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected = cases
    if ids:
        wanted = set(ids)
        selected = [case for case in selected if case["id"] in wanted]
    if groups:
        wanted_groups = set(groups)
        selected = [case for case in selected if case.get("group") in wanted_groups]
    if limit is not None:
        selected = selected[:limit]
    return selected


def run_cases(
    cases: list[dict[str, Any]],
    *,
    baseline: dict[str, dict[str, Any]] | None = None,
    fail_on_regression: bool = False,
    reader_factory: ReaderFactory = UnlimitedSearchReader,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        rows.append(run_case(case, baseline=baseline or {}, fail_on_regression=fail_on_regression, reader_factory=reader_factory))
    return rows


def run_case(
    case: dict[str, Any],
    *,
    baseline: dict[str, dict[str, Any]],
    fail_on_regression: bool,
    reader_factory: ReaderFactory = UnlimitedSearchReader,
) -> dict[str, Any]:
    started = time.monotonic()
    mode = str(case.get("mode") or "read")
    try:
        if mode == "media":
            payload = extract_media_metadata(case["url"], timeout=int(case.get("timeout", 90))).to_dict()
        else:
            reader = reader_factory()
            result = reader.read_public_url(
                case["url"],
                timeout=int(case.get("timeout", 25)),
                max_attempts=int(case.get("max_attempts", 12)),
                max_content_chars=int(case.get("max_content_chars", 4000)),
                enable_public_routes=bool(case.get("enable_public_routes", True)),
                preferred_identity=case.get("preferred_identity"),
                success_selectors=case.get("success_selectors"),
            )
            payload = result.to_dict(include_content=False)
    except Exception as exc:
        payload = {
            "ok": False,
            "verdict": "unknown",
            "stop_reason": "exception",
            "summary": f"{type(exc).__name__}:{str(exc)[:240]}",
            "metadata": {},
            "trace": [],
            "content_length": 0,
        }

    row = compact_result(case, payload, elapsed_ms=int((time.monotonic() - started) * 1000))
    failures = expectation_failures(row, case.get("expect") or {})
    row["expectation_failures"] = failures
    row["passed"] = not failures
    row["regressions"] = regression_failures(row, baseline.get(case["id"]))
    required = bool(case.get("required", True))
    if row["regressions"] and fail_on_regression:
        row["status"] = "regression"
    elif failures and required:
        row["status"] = "fail"
    elif failures:
        row["status"] = "warn"
    else:
        row["status"] = "pass"
    return row


def compact_result(case: dict[str, Any], payload: dict[str, Any], *, elapsed_ms: int) -> dict[str, Any]:
    metadata = payload.get("metadata") or {}
    route = metadata.get("route")
    platform = metadata.get("platform")
    trace = payload.get("trace") or []
    if (not route or not platform) and trace:
        last = trace[-1]
        route = route or last.get("executor")
        platform = platform or last.get("phase")
    return {
        "id": case["id"],
        "group": case.get("group", ""),
        "url": case["url"],
        "required": bool(case.get("required", True)),
        "mode": case.get("mode", "read"),
        "ok": bool(payload.get("ok")),
        "verdict": payload.get("verdict") or "",
        "stop_reason": payload.get("stop_reason") or "",
        "content_length": int(payload.get("content_length") or 0),
        "platform": platform or "",
        "route": route or "",
        "fallback_verdict": metadata.get("fallback_verdict", ""),
        "summary": payload.get("summary") or payload.get("error") or "",
        "final_url": payload.get("final_url") or payload.get("url") or "",
        "elapsed_ms": elapsed_ms,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def expectation_failures(row: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if "ok" in expect and bool(row["ok"]) is not bool(expect["ok"]):
        failures.append(f"ok expected {expect['ok']} got {row['ok']}")
    if expect.get("platform") and row["platform"] != expect["platform"]:
        failures.append(f"platform expected {expect['platform']} got {row['platform']}")
    if expect.get("route") and row["route"] != expect["route"]:
        failures.append(f"route expected {expect['route']} got {row['route']}")
    if expect.get("verdict_in") and row["verdict"] not in set(expect["verdict_in"]):
        failures.append(f"verdict {row['verdict']} not in {expect['verdict_in']}")
    if expect.get("stop_reason_in") and row["stop_reason"] not in set(expect["stop_reason_in"]):
        failures.append(f"stop_reason {row['stop_reason']} not in {expect['stop_reason_in']}")
    if expect.get("stop_reason_not_in") and row["stop_reason"] in set(expect["stop_reason_not_in"]):
        failures.append(f"stop_reason {row['stop_reason']} is disallowed")
    min_content_length = expect.get("min_content_length")
    if min_content_length is not None and row["content_length"] < int(min_content_length):
        failures.append(f"content_length expected >= {min_content_length} got {row['content_length']}")
    return failures


def regression_failures(row: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
    if not previous:
        return []
    failures: list[str] = []
    if previous.get("ok") is True and row["ok"] is False:
        failures.append("ok regressed true -> false")
    if previous.get("platform") and row["platform"] and previous.get("platform") != row["platform"]:
        failures.append(f"platform changed {previous.get('platform')} -> {row['platform']}")
    if previous.get("route") and row["route"] and previous.get("route") != row["route"]:
        failures.append(f"route changed {previous.get('route')} -> {row['route']}")
    return failures


def load_jsonl_by_id(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[str(row["id"])] = row
    return rows


def output_path_for(raw_output: str | None) -> Path:
    if raw_output:
        return Path(raw_output)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_DIR / f"eval-{stamp}.jsonl"


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# unlimited-search live eval",
        "",
        f"- total: {len(rows)}",
        *[f"- {status}: {counts[status]}" for status in sorted(counts)],
        "",
        "| status | id | group | platform | route | verdict | ms | summary |",
        "|---|---|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {status} | {id} | {group} | {platform} | {route} | {verdict} | {elapsed_ms} | {summary} |".format(
                status=_md(row["status"]),
                id=_md(row["id"]),
                group=_md(row["group"]),
                platform=_md(row["platform"]),
                route=_md(row["route"]),
                verdict=_md(row["verdict"]),
                elapsed_ms=row["elapsed_ms"],
                summary=_md(row["summary"][:160]),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "status",
        "id",
        "group",
        "url",
        "ok",
        "verdict",
        "stop_reason",
        "platform",
        "route",
        "content_length",
        "elapsed_ms",
        "summary",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def print_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    total = len(rows)
    summary = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"eval results: total={total}" + (f", {summary}" if summary else ""))
    print(f"wrote: {output_path}")
    for row in rows:
        status = row["status"].upper()
        print(f"{status}\t{row['id']}\t{row['platform']}:{row['route']}\t{row['verdict']}\t{row['summary'][:120]}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run live URL regression evals and write JSONL results.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="YAML eval case file")
    parser.add_argument("--output", help="JSONL output path; defaults to eval-results/eval-<timestamp>.jsonl")
    parser.add_argument("--markdown", help="Optional Markdown report path")
    parser.add_argument("--csv", help="Optional CSV report path")
    parser.add_argument("--baseline", help="Previous JSONL result to compare against")
    parser.add_argument("--fail-on-regression", action="store_true", help="Exit non-zero when baseline comparison regresses")
    parser.add_argument("--id", action="append", help="Run only a case id; can be repeated")
    parser.add_argument("--group", action="append", help="Run only a group; can be repeated")
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases")
    parser.add_argument("--list", action="store_true", help="List selected cases without running them")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
