from pathlib import Path
import importlib.util

from unlimited_search.engine.models import FetchResult, Verdict


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
SPEC = importlib.util.spec_from_file_location("run_eval", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
run_eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_eval)


class FakeReader:
    def read_public_url(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        return FetchResult(
            ok=True,
            content="x" * 42,
            final_url=url,
            verdict=Verdict.STRONG_OK,
            summary="public route succeeded: github:search-repositories",
            stop_reason="success",
            metadata={"platform": "github", "route": "search-repositories"},
        )


def test_run_case_compacts_success_and_expectations() -> None:
    row = run_eval.run_case(
        {
            "id": "github_search",
            "url": "https://github.com/search?q=unlimited+search&type=repositories",
            "expect": {"ok": True, "platform": "github", "route": "search-repositories", "min_content_length": 10},
        },
        baseline={},
        fail_on_regression=False,
        reader_factory=FakeReader,
    )

    assert row["status"] == "pass"
    assert row["passed"] is True
    assert row["content_length"] == 42
    assert row["platform"] == "github"
    assert row["route"] == "search-repositories"


def test_optional_expectation_failure_is_warn() -> None:
    row = run_eval.run_case(
        {
            "id": "hard_site",
            "url": "https://example.com",
            "required": False,
            "expect": {"ok": False},
        },
        baseline={},
        fail_on_regression=False,
        reader_factory=FakeReader,
    )

    assert row["status"] == "warn"
    assert row["expectation_failures"]


def test_baseline_regression_can_fail() -> None:
    row = run_eval.run_case(
        {
            "id": "github_search",
            "url": "https://github.com/search?q=unlimited+search&type=repositories",
            "expect": {"ok": True},
        },
        baseline={"github_search": {"id": "github_search", "ok": True, "platform": "hacker-news", "route": "algolia-search"}},
        fail_on_regression=True,
        reader_factory=FakeReader,
    )

    assert row["status"] == "regression"
    assert row["regressions"]


def test_load_cases_merges_defaults(tmp_path: Path) -> None:
    cases_file = tmp_path / "cases.yaml"
    cases_file.write_text(
        """
version: 1
defaults:
  timeout: 3
  expect:
    stop_reason_not_in: [unsafe_url]
cases:
  - id: one
    url: https://example.com
    expect:
      ok: true
""",
        encoding="utf-8",
    )

    cases = run_eval.load_cases(cases_file)

    assert cases[0]["timeout"] == 3
    assert cases[0]["expect"] == {"stop_reason_not_in": ["unsafe_url"], "ok": True}


def test_report_writers_create_markdown_and_csv(tmp_path: Path) -> None:
    rows = [
        {
            "status": "pass",
            "id": "one",
            "group": "stable",
            "url": "https://example.com",
            "ok": True,
            "verdict": "strong_ok",
            "stop_reason": "success",
            "platform": "example",
            "route": "route",
            "content_length": 42,
            "elapsed_ms": 12,
            "summary": "ok",
        }
    ]
    markdown = tmp_path / "report.md"
    csv_path = tmp_path / "report.csv"

    run_eval.write_markdown(rows, markdown)
    run_eval.write_csv(rows, csv_path)

    assert "| pass | one | stable | example | route | strong_ok | 12 | ok |" in markdown.read_text(encoding="utf-8")
    assert "status,id,group,url,ok,verdict,stop_reason,platform,route,content_length,elapsed_ms,summary" in csv_path.read_text(
        encoding="utf-8"
    )
