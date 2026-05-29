from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig


@dataclass(frozen=True)
class Memo:
    id: int
    content: str
    created_at: str


@dataclass(frozen=True)
class CachedResponse:
    response: str
    score: float = 1.0


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
            """
        )
        _ensure_column(connection, "response_cache", "prompt_hash", "TEXT")
        _ensure_column(connection, "response_cache", "model", "TEXT")
        _ensure_column(connection, "response_cache", "options_hash", "TEXT")
        _ensure_column(connection, "response_cache", "expires_at", "TEXT")

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


def get_cached_response(
    prompt: str,
    *,
    model: str | None = None,
    options_hash: str | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> str | None:
    normalized = normalize_prompt(prompt)
    if not normalized:
        return None

    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        if model is None and options_hash is None:
            row = connection.execute(
                "SELECT response FROM response_cache WHERE prompt = ?",
                (normalized,),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT response
                FROM response_cache
                WHERE prompt = ?
                  AND COALESCE(model, '') = COALESCE(?, '')
                  AND COALESCE(options_hash, '') = COALESCE(?, '')
                  AND (expires_at IS NULL OR expires_at > ?)
                """,
                (normalized, model, options_hash, now),
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
    model: str | None = None,
    options_hash: str | None = None,
    expires_at: str | None = None,
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
            INSERT INTO response_cache(
                prompt,
                response,
                created_at,
                prompt_hash,
                model,
                options_hash,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(prompt) DO UPDATE SET
                response = excluded.response,
                prompt_hash = excluded.prompt_hash,
                model = excluded.model,
                options_hash = excluded.options_hash,
                expires_at = excluded.expires_at
            """,
            (
                normalized,
                response.strip(),
                now,
                stable_hash(normalized),
                model,
                options_hash,
                expires_at,
            ),
        )


def get_similar_cached_response(
    prompt: str,
    *,
    model: str | None = None,
    options_hash: str | None = None,
    min_score: float = 0.82,
    config: AppConfig = DEFAULT_CONFIG,
) -> CachedResponse | None:
    normalized = normalize_prompt(prompt)
    tokens = _token_set(normalized)
    if len(tokens) < 2:
        return None

    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        rows = connection.execute(
            """
            SELECT prompt, response
            FROM response_cache
            WHERE COALESCE(model, '') = COALESCE(?, '')
              AND COALESCE(options_hash, '') = COALESCE(?, '')
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY hit_count DESC, created_at DESC
            LIMIT 50
            """,
            (model, options_hash, now),
        ).fetchall()

        best_row = None
        best_score = 0.0
        for row in rows:
            score = _jaccard_score(tokens, _token_set(str(row["prompt"])))
            if score > best_score:
                best_score = score
                best_row = row

        if best_row is None or best_score < min_score:
            return None

        connection.execute(
            """
            UPDATE response_cache
            SET hit_count = hit_count + 1,
                last_hit_at = ?
            WHERE prompt = ?
            """,
            (now, str(best_row["prompt"])),
        )

    return CachedResponse(response=str(best_row["response"]), score=best_score)


def get_cached_document_summary(
    path: Path,
    file_hash: str,
    max_chars: int,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> str | None:
    cache_key = document_cache_key(file_hash, max_chars)
    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        row = connection.execute(
            "SELECT summary FROM document_summary_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """
            UPDATE document_summary_cache
            SET hit_count = hit_count + 1,
                last_hit_at = ?
            WHERE cache_key = ?
            """,
            (now, cache_key),
        )
    return str(row["summary"])


def save_document_summary(
    path: Path,
    file_hash: str,
    max_chars: int,
    summary: str,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> None:
    if not summary.strip():
        return

    cache_key = document_cache_key(file_hash, max_chars)
    initialize_database(config=config)
    now = _utc_now()
    with _connect(config.resolved_database_path) as connection:
        connection.execute(
            """
            INSERT INTO document_summary_cache(
                cache_key,
                path,
                file_hash,
                max_chars,
                summary,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                path = excluded.path,
                summary = excluded.summary
            """,
            (cache_key, str(path), file_hash, max_chars, summary.strip(), now),
        )


def normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.casefold().split())


def stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def document_cache_key(file_hash: str, max_chars: int) -> str:
    return stable_hash(f"document-summary:{file_hash}:{max_chars}")


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if any(str(row["name"]) == column for row in rows):
        return
    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _token_set(prompt: str) -> set[str]:
    return {token for token in prompt.split() if token}


def _jaccard_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
