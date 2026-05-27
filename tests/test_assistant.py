from deskmate_ai.assistant import handle_prompt
from deskmate_ai.config import AppConfig
from deskmate_ai.core import assistant as assistant_module


def test_empty_prompt_returns_message() -> None:
    result = handle_prompt("")

    assert result.action == "empty"
    assert "입력" in result.message


def test_fallback_for_unknown_prompt(tmp_path, monkeypatch) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    monkeypatch.setattr(assistant_module, "ask_local_model", lambda *args, **kwargs: None)

    result = handle_prompt("오늘 뭐 할까?", config=config)

    assert result.action == "fallback"
    assert "문서 요약" in result.message


def test_local_profile_request_skips_llm(tmp_path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    stored = handle_prompt("내 이름은 민수", config=config)
    fetched = handle_prompt("내 이름 뭐야?", config=config)

    assert stored.action == "set_profile"
    assert fetched.action == "get_profile"
    assert "민수" in fetched.message


def test_local_memo_request_skips_llm(tmp_path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    stored = handle_prompt("기억해 SQLite 캐시 먼저 만들기", config=config)
    fetched = handle_prompt("최근 메모 보여줘", config=config)

    assert stored.action == "add_memo"
    assert fetched.action == "list_memos"
    assert "SQLite 캐시" in fetched.message
