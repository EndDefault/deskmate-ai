from pathlib import Path

from deskmate_ai.config import AppConfig
from deskmate_ai.services.storage_service import (
    add_memo,
    delete_keyword_cache,
    find_keyword_cache_in_text,
    get_cached_document_summary,
    get_cached_response,
    get_keyword_cache,
    get_keyword_cache_by_keyword,
    get_keyword_cache_category,
    get_profile_value,
    get_similar_cached_response,
    initialize_database,
    list_keyword_cache_categories,
    list_recent_memos,
    list_translation_cache_groups,
    save_cached_response,
    save_document_summary,
    save_keyword_cache,
    save_keyword_cache_category,
    save_translation_cache_group,
    set_profile_value,
)


def test_initialize_database_creates_sqlite_file(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    path = initialize_database(config=config)

    assert path.exists()


def test_profile_round_trip(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    set_profile_value("name", "Codex", config=config)

    assert get_profile_value("name", config=config) == "Codex"


def test_memo_round_trip(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    add_memo("check sqlite cache", config=config)

    memos = list_recent_memos(config=config)
    assert memos[0].content == "check sqlite cache"


def test_response_cache_normalizes_prompt(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    save_cached_response(" Hello   DeskMate ", "cached answer", config=config)

    assert get_cached_response("hello deskmate", config=config) == "cached answer"


def test_response_cache_separates_model_options(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    save_cached_response(
        "hello deskmate",
        "cached answer",
        model="qwen3:4b",
        options_hash="fast",
        config=config,
    )

    assert get_cached_response("hello deskmate", model="qwen3:4b", options_hash="fast", config=config) == "cached answer"
    assert get_cached_response("hello deskmate", model="llama3.2:3b", options_hash="fast", config=config) is None


def test_similar_response_cache_returns_high_confidence_match(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    save_cached_response(
        "python cache design local llm response",
        "cached answer",
        model="qwen3:4b",
        options_hash="fast",
        config=config,
    )

    cached = get_similar_cached_response(
        "python cache design local llm response please",
        model="qwen3:4b",
        options_hash="fast",
        config=config,
    )

    assert cached is not None
    assert cached.response == "cached answer"


def test_document_summary_cache_round_trip(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    document = tmp_path / "note.md"
    file_hash = "abc123"

    save_document_summary(document, file_hash, 1200, "summary", config=config)

    assert get_cached_document_summary(document, file_hash, 1200, config=config) == "summary"


def test_keyword_cache_categories_round_trip(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    saved = save_keyword_cache_category("사이트 캐시", config=config)
    categories = list_keyword_cache_categories(config=config)

    assert saved in categories
    assert get_keyword_cache_category(saved.id, config=config) == saved


def test_keyword_cache_round_trip(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    category = save_keyword_cache_category("사이트 캐시", config=config)

    saved = save_keyword_cache(
        "아카라이브",
        "https://arca.live",
        category_id=category.id,
        action_type="open_url",
        config=config,
    )
    fetched = get_keyword_cache_by_keyword(" 아카라이브", category_ids=[category.id], config=config)

    assert fetched == saved
    assert fetched is not None
    assert fetched.category_id == category.id
    assert fetched.action_type == "open_url"
    assert get_keyword_cache(saved.id, config=config) == saved


def test_keyword_cache_respects_category_filter(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    first_category = save_keyword_cache_category("첫 번째", config=config)
    second_category = save_keyword_cache_category("두 번째", config=config)
    save_keyword_cache("공통", "first", category_id=first_category.id, config=config)
    second = save_keyword_cache("공통", "second", category_id=second_category.id, config=config)

    fetched = get_keyword_cache_by_keyword("공통", category_ids=[second_category.id], config=config)

    assert fetched == second


def test_keyword_cache_updates_existing_keyword(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    first = save_keyword_cache("아카라이브", "old", config=config)
    updated = save_keyword_cache("아카라이브", "new", action_type="open_url", config=config)

    assert updated.id == first.id
    assert updated.action_type == "open_url"
    assert updated.content == "new"


def test_keyword_cache_delete(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    saved = save_keyword_cache("아카라이브", "https://arca.live", config=config)

    assert delete_keyword_cache(saved.id, config=config)
    assert get_keyword_cache(saved.id, config=config) is None


def test_find_keyword_cache_in_text(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")
    saved = save_keyword_cache("아카라이브", "https://arca.live", action_type="open_url", config=config)

    matched = find_keyword_cache_in_text("아카라이브 사이트 열어줘", config=config)

    assert matched == saved


def test_translation_cache_group_default_exists(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    groups = list_translation_cache_groups(config=config)

    assert any(group.name == "일본어 캐시" for group in groups)


def test_translation_cache_group_round_trip(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    saved = save_translation_cache_group("중국어 캐시", "zh", "ko", config=config)
    groups = list_translation_cache_groups(config=config)

    assert saved in groups
