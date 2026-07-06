from unlimited_search.server import diagnose_access


def test_server_tool_function_returns_dict() -> None:
    result = diagnose_access(
        "http://127.0.0.1:8000/private",
        max_attempts=1,
        enable_public_routes=False,
    )

    assert result["ok"] is False
    assert result["verdict"] == "unsafe_url"
    assert "trace" in result
