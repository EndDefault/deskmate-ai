from __future__ import annotations

import sqlite3
from pathlib import Path

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.sqlite.connection import connect, utc_now


def initialize_database(*, config: AppConfig = DEFAULT_CONFIG) -> Path:
    path = config.resolved_database_path
    path.parent.mkdir(parents=True, exist_ok=True)

    with connect(path) as connection:
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
                last_hit_at TEXT,
                prompt_hash TEXT,
                model TEXT,
                options_hash TEXT,
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS document_summary_cache (
                cache_key TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                max_chars INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                hit_count INTEGER NOT NULL DEFAULT 0,
                last_hit_at TEXT
            );

            CREATE TABLE IF NOT EXISTS keyword_cache_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS keyword_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL DEFAULT 1,
                keyword TEXT NOT NULL,
                keyword_normalized TEXT NOT NULL,
                action_type TEXT NOT NULL DEFAULT 'show_text',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(category_id, keyword_normalized)
            );

            CREATE TABLE IF NOT EXISTS translation_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES keyword_cache_categories(id) ON DELETE CASCADE,
                UNIQUE(category_id, source_text)
            );

            CREATE TABLE IF NOT EXISTS translation_cache_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source_language TEXT NOT NULL DEFAULT 'en',
                target_language TEXT NOT NULL DEFAULT 'ko',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS translation_cache_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                source_language TEXT NOT NULL,
                target_language TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(group_id) REFERENCES translation_cache_groups(id) ON DELETE CASCADE,
                UNIQUE(group_id, source_language, target_language, source_text)
            );
            """
        )
        _ensure_column(connection, "response_cache", "prompt_hash", "TEXT")
        _ensure_column(connection, "response_cache", "model", "TEXT")
        _ensure_column(connection, "response_cache", "options_hash", "TEXT")
        _ensure_column(connection, "response_cache", "expires_at", "TEXT")
        _ensure_default_keyword_cache_categories(connection)
        _ensure_default_translation_cache_groups(connection)
        _ensure_column(connection, "keyword_cache", "category_id", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(connection, "keyword_cache", "action_type", "TEXT NOT NULL DEFAULT 'show_text'")

    return path


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if any(str(row["name"]) == column for row in rows):
        return
    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_default_keyword_cache_categories(connection: sqlite3.Connection) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO keyword_cache_categories(id, name, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (1, "湲곕낯 罹먯떆", now, now),
    )


def _ensure_default_translation_cache_groups(connection: sqlite3.Connection) -> None:
    now = utc_now()
    for name in ("기본 번역 캐시", "만화 상황 캐시"):
        connection.execute(
            """
            INSERT INTO translation_cache_groups(name, source_language, target_language, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            (name, "en", "ko", now, now),
        )
    connection.execute(
        """
        INSERT INTO keyword_cache_categories(name, created_at, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO NOTHING
        """,
        ("일본어 캐시", now, now),
    )
