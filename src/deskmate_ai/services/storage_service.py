from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig


@dataclass(frozen=True)
class Memo:
    id: int
    content: str
    created_at: str


def initialize_database(*, config: AppConfig = DEFAULT_CONFIG) -> Path:
    path = config.resolved_database_path
    path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS response_cache (
                prompt TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                hit_count INTEGER NOT NULL DEFAULT 0,
                last_hit_at TEXT
            );
            """
        )

    return path


def get_profile_value(key: str, *, config: AppConfig = DEFAULT_CONFIG) -> str | None:
    initialize_database(config=config)
    with _connect(config.resolved_database_path) as connection:
        row = connection.execute(
            "SELECT value FROM user_profile WHERE key = ?",
            (key,),
        ).fetchone()
    return None if row is None else str(row["value"])


def set_profile_value(key: str, value: str, *, config: AppConfig = DEFAULT_CONFIG) -> None:
    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
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


def add_memo(content: str, *, config: AppConfig = DEFAULT_CONFIG) -> Memo:
    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO memos(content, created_at) VALUES (?, ?)",
            (content, now),
        )
        memo_id = int(cursor.lastrowid)
    return Memo(id=memo_id, content=content, created_at=now)


def list_recent_memos(limit: int = 5, *, config: AppConfig = DEFAULT_CONFIG) -> list[Memo]:
    initialize_database(config=config)
    with _connect(config.resolved_database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, content, created_at
            FROM memos
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        Memo(id=int(row["id"]), content=str(row["content"]), created_at=str(row["created_at"]))
        for row in rows
    ]


def get_cached_response(prompt: str, *, config: AppConfig = DEFAULT_CONFIG) -> str | None:
    normalized = normalize_prompt(prompt)
    if not normalized:
        return None

    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        row = connection.execute(
            "SELECT response FROM response_cache WHERE prompt = ?",
            (normalized,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """
            UPDATE response_cache
            SET hit_count = hit_count + 1,
                last_hit_at = ?
            WHERE prompt = ?
            """,
            (now, normalized),
        )
    return str(row["response"])


def save_cached_response(
    prompt: str,
    response: str,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> None:
    normalized = normalize_prompt(prompt)
    if not normalized or not response.strip():
        return

    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        connection.execute(
            """
            INSERT INTO response_cache(prompt, response, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(prompt) DO UPDATE SET
                response = excluded.response
            """,
            (normalized, response.strip(), now),
        )


def normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.casefold().split())


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
