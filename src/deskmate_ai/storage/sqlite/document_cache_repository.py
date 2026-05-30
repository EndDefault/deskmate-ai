from __future__ import annotations

from pathlib import Path

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.sqlite.connection import connect, utc_now
from deskmate_ai.storage.sqlite.schema import initialize_database
from deskmate_ai.storage.sqlite.utils import document_cache_key


def get_cached_document_summary(
    path: Path,
    file_hash: str,
    max_chars: int,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> str | None:
    cache_key = document_cache_key(file_hash, max_chars)
    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        row = connection.execute("SELECT summary FROM document_summary_cache WHERE cache_key = ?", (cache_key,)).fetchone()
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
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
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
