from __future__ import annotations

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.sqlite.connection import connect, utc_now
from deskmate_ai.storage.sqlite.schema import initialize_database


def get_profile_value(key: str, *, config: AppConfig = DEFAULT_CONFIG) -> str | None:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        row = connection.execute("SELECT value FROM user_profile WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def set_profile_value(key: str, value: str, *, config: AppConfig = DEFAULT_CONFIG) -> None:
    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        connection.execute(
            """
            INSERT INTO user_profile(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
