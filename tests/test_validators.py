from unlimited_search.engine.models import ResponseEnvelope, Verdict
from unlimited_search.engine.validators import validate_response


def test_nonempty_json_is_weak_ok() -> None:
    response = ResponseEnvelope(
        status_code=200,
        text='{"title":"hello"}',
        url="https://example.com/api",
        headers={"content-type": "application/json"},
    )

    result = validate_response(response)

    assert result.verdict == Verdict.WEAK_OK
    assert "json_ok" in result.reasons


def test_cloudflare_marker_is_challenge() -> None:
    response = ResponseEnvelope(
        status_code=403,
        text="<html><title>Attention Required! | Cloudflare</title></html>",
        url="https://example.com",
    )

    result = validate_response(response)

    assert result.verdict == Verdict.CHALLENGE


def test_success_selector_is_strong_ok() -> None:
    response = ResponseEnvelope(
        status_code=200,
        text="<html><body><article>content</article></body></html>",
        url="https://example.com",
    )

    result = validate_response(response, success_selectors=["article"])

    assert result.verdict == Verdict.STRONG_OK
    assert result.matched_selectors == ["article"]


def test_large_public_page_with_sign_in_text_is_not_auth_wall() -> None:
    response = ResponseEnvelope(
        status_code=200,
        text="<html><head><meta property='og:title' content='Repo'></head>"
        "<body><main><article>public content</article></main>"
        + ("sign in to continue " * 2000)
        + "</body></html>",
        url="https://example.com/public",
    )

    result = validate_response(response)

    assert result.verdict == Verdict.WEAK_OK
    assert "login_marker_nonterminal" in result.reasons


def test_large_public_page_with_captcha_word_is_not_challenge() -> None:
    response = ResponseEnvelope(
        status_code=200,
        text="<html><head><meta property='og:title' content='Repo'></head>"
        "<body><main><article>public content</article></main>"
        + ("captcha " * 4000)
        + "</body></html>",
        url="https://example.com/public",
    )

    result = validate_response(response)

    assert result.verdict == Verdict.WEAK_OK
    assert "soft_nonterminal:captcha" in result.reasons


def test_tiktok_slardar_waf_shell_is_challenge() -> None:
    response = ResponseEnvelope(
        status_code=200,
        text="""<!DOCTYPE html><html><head>
        <script id="slardar-config" type="application/json">{"slardarClient":"SlardarWAF"}</script>
        </head><body>Please wait...
        <p id="wci" class="_wafchallengeid"></p>
        <p id="rci" class="waforiginalreid"></p>
        <script src="/obj/waf-aiso/dd9808.js"></script>
        </body></html>""",
        url="https://www.tiktok.com/@openai",
    )

    result = validate_response(response)

    assert result.verdict == Verdict.CHALLENGE
    assert any(reason.startswith("hard:") for reason in result.reasons)


def test_large_profile_page_with_script_captcha_word_can_be_ok() -> None:
    response = ResponseEnvelope(
        status_code=200,
        text="<html><head><title>TikTok - Make Your Day</title>"
        '<script>{"captcha":"script-only telemetry"}</script></head><body>'
        "<h1>OpenAI @ openai</h1><p>853.1K Followers 5.2M Likes</p>"
        "<p>OpenAI's mission is to ensure artificial intelligence benefits all of humanity.</p>"
        + ("x" * 25_000)
        + "</body></html>",
        url="https://www.tiktok.com/@openai",
    )

    result = validate_response(response)

    assert result.verdict == Verdict.WEAK_OK
    assert "soft_nonterminal:captcha" in result.reasons
