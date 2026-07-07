import io
from pathlib import Path

import unlimited_search.app as app


class TtyStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


class NonTtyStringIO(io.StringIO):
    def isatty(self) -> bool:
        return False


def test_star_prompt_yes_opens_browser_once(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    opened_urls: list[str] = []

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.sys, "stdin", TtyStringIO("y\n"))
    monkeypatch.setattr(app.sys, "stdout", TtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", TtyStringIO())
    monkeypatch.setattr(app.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True)

    app._maybe_prompt_for_star("help")
    app._maybe_prompt_for_star("help")

    assert opened_urls == [app.STAR_URL]
    assert (tmp_path / "star_prompt_seen").exists()


def test_star_prompt_no_does_not_open_browser(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    opened_urls: list[str] = []

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.sys, "stdin", TtyStringIO("n\n"))
    monkeypatch.setattr(app.sys, "stdout", TtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", TtyStringIO())
    monkeypatch.setattr(app.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True)

    app._maybe_prompt_for_star("help")

    assert opened_urls == []
    assert (tmp_path / "star_prompt_seen").exists()


def test_star_prompt_skips_non_interactive(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    opened_urls: list[str] = []

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.sys, "stdin", NonTtyStringIO("y\n"))
    monkeypatch.setattr(app.sys, "stdout", NonTtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", NonTtyStringIO())
    monkeypatch.setattr(app.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True)

    app._maybe_prompt_for_star("help")

    assert opened_urls == []
    assert not (tmp_path / "star_prompt_seen").exists()


def test_star_prompt_skips_serve(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    opened_urls: list[str] = []

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.sys, "stdin", TtyStringIO("y\n"))
    monkeypatch.setattr(app.sys, "stdout", TtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", TtyStringIO())
    monkeypatch.setattr(app.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True)

    app._maybe_prompt_for_star("serve")

    assert opened_urls == []
    assert not (tmp_path / "star_prompt_seen").exists()


def test_star_prompt_skips_unknown_command(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    opened_urls: list[str] = []

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.sys, "stdin", TtyStringIO("y\n"))
    monkeypatch.setattr(app.sys, "stdout", TtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", TtyStringIO())
    monkeypatch.setattr(app.webbrowser, "open", lambda url, new=0: opened_urls.append(url) or True)

    app._maybe_prompt_for_star("wat")

    assert opened_urls == []
    assert not (tmp_path / "star_prompt_seen").exists()


def test_star_prompt_warns_when_browser_does_not_open(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    stderr = TtyStringIO()

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.sys, "stdin", TtyStringIO("y\n"))
    monkeypatch.setattr(app.sys, "stdout", TtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", stderr)
    monkeypatch.setattr(app.webbrowser, "open", lambda url, new=0: False)

    app._maybe_prompt_for_star("help")

    assert "warning: could not open browser" in stderr.getvalue()
    assert (tmp_path / "star_prompt_seen").exists()


def test_main_does_not_prompt_before_serve(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    called = {"serve": False}

    monkeypatch.setenv(app.STAR_PROMPT_STATE_ENV, str(tmp_path))
    monkeypatch.setattr(app.server, "main", lambda: called.__setitem__("serve", True))
    monkeypatch.setattr(app.sys, "stdin", TtyStringIO("y\n"))
    monkeypatch.setattr(app.sys, "stdout", TtyStringIO())
    monkeypatch.setattr(app.sys, "stderr", TtyStringIO())

    assert app.main(["serve"]) is None
    assert called["serve"] is True
    assert not (tmp_path / "star_prompt_seen").exists()
