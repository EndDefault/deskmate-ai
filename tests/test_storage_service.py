from pathlib import Path

from deskmate_ai.config import AppConfig
from deskmate_ai.services.storage_service import (
    add_memo,
    get_cached_response,
    get_profile_value,
    initialize_database,
    list_recent_memos,
    save_cached_response,
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
