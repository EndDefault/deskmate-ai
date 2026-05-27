from deskmate_ai.assistant import handle_prompt


def test_empty_prompt_returns_message() -> None:
    result = handle_prompt("")

    assert result.action == "empty"
    assert "입력" in result.message


def test_fallback_for_unknown_prompt() -> None:
    result = handle_prompt("오늘 뭐 할까?")

    assert result.action == "fallback"
    assert "문서 요약" in result.message
