from deskmate_ai.assistant import handle_prompt
from deskmate_ai.config import AppConfig
from deskmate_ai.core import assistant as assistant_module
from deskmate_ai.services import web_service
from deskmate_ai.services.storage_service import save_keyword_cache


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


def test_similar_cache_skips_llm(tmp_path, monkeypatch) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    calls = {"count": 0}

    def fake_model(*args, **kwargs):
        calls["count"] += 1
        return "캐시할 답변"

    monkeypatch.setattr(assistant_module, "ask_local_model", fake_model)

    first = handle_prompt("python cache design local llm response", config=config)
    second = handle_prompt("python cache design local llm response please", config=config)

    assert first.action == "ask_local_model"
    assert second.action == "similar_cached_response"
    assert second.message == "캐시할 답변"
    assert calls["count"] == 1


def test_keyword_cache_shows_text(tmp_path, monkeypatch) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    save_keyword_cache("아카라이브", "https://arca.live", config=config)
    monkeypatch.setattr(assistant_module, "ask_local_model", lambda *args, **kwargs: None)

    result = handle_prompt("아카라이브", config=config)

    assert result.action == "keyword_cache"
    assert result.message == "https://arca.live"


def test_keyword_cache_can_be_disabled_by_empty_category_selection(tmp_path, monkeypatch) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    save_keyword_cache("아카라이브", "https://arca.live", config=config)
    monkeypatch.setattr(assistant_module, "ask_local_model", lambda *args, **kwargs: None)

    result = handle_prompt("아카라이브", cache_category_ids=[], config=config)

    assert result.action == "fallback"


def test_open_url_keyword_cache_opens_without_open_word(tmp_path, monkeypatch) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    opened: list[str] = []
    save_keyword_cache("아카라이브", "https://arca.live", action_type="open_url", config=config)
    monkeypatch.setattr(web_service.webbrowser, "open", opened.append)

    result = handle_prompt("아카라이브", config=config)

    assert result.action == "open_keyword_cache"
    assert "https://arca.live" in result.message
    assert opened == ["https://arca.live"]


def test_open_url_keyword_cache_opens_when_prompt_contains_keyword(tmp_path, monkeypatch) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    opened: list[str] = []
    save_keyword_cache("아카라이브", "https://arca.live", action_type="open_url", config=config)
    monkeypatch.setattr(web_service.webbrowser, "open", opened.append)

    result = handle_prompt("아카라이브 사이트 열어줘", config=config)

    assert result.action == "open_keyword_cache"
    assert "https://arca.live" in result.message
    assert opened == ["https://arca.live"]
