from __future__ import annotations

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.models import TranslationCacheGroup, TranslationTerm
from deskmate_ai.storage.sqlite.connection import connect, utc_now
from deskmate_ai.storage.sqlite.schema import initialize_database
from deskmate_ai.storage.sqlite.utils import translation_cache_group_from_row, translation_term_from_row


def list_translation_cache_groups(*, config: AppConfig = DEFAULT_CONFIG) -> list[TranslationCacheGroup]:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, name, source_language, target_language, created_at, updated_at
            FROM translation_cache_groups
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
    return [translation_cache_group_from_row(row) for row in rows]


def get_translation_cache_group(
    group_id: int,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> TranslationCacheGroup | None:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        row = connection.execute(
            """
            SELECT id, name, source_language, target_language, created_at, updated_at
            FROM translation_cache_groups
            WHERE id = ?
            """,
            (group_id,),
        ).fetchone()
    return None if row is None else translation_cache_group_from_row(row)


def save_translation_cache_group(
    name: str,
    source_language: str,
    target_language: str,
    *,
    group_id: int | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> TranslationCacheGroup:
    name = name.strip()
    if not name:
        raise ValueError("name is required")

    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        if group_id is None:
            cursor = connection.execute(
                """
                INSERT INTO translation_cache_groups(name, source_language, target_language, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    source_language = excluded.source_language,
                    target_language = excluded.target_language,
                    updated_at = excluded.updated_at
                RETURNING id, name, source_language, target_language, created_at, updated_at
                """,
                (name, source_language, target_language, now, now),
            )
        else:
            cursor = connection.execute(
                """
                UPDATE translation_cache_groups
                SET name = ?,
                    source_language = ?,
                    target_language = ?,
                    updated_at = ?
                WHERE id = ?
                RETURNING id, name, source_language, target_language, created_at, updated_at
                """,
                (name, source_language, target_language, now, group_id),
            )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"translation cache group not found: {group_id}")
    return translation_cache_group_from_row(row)


def delete_translation_cache_group(group_id: int, *, config: AppConfig = DEFAULT_CONFIG) -> bool:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        connection.execute("DELETE FROM translation_cache_terms WHERE group_id = ?", (group_id,))
        cursor = connection.execute("DELETE FROM translation_cache_groups WHERE id = ?", (group_id,))
    return cursor.rowcount > 0


def list_translation_terms(
    *,
    group_id: int | None = None,
    source_language: str | None = None,
    target_language: str | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> list[TranslationTerm]:
    initialize_database(config=config)
    clauses: list[str] = []
    params: list[object] = []
    if group_id is not None:
        clauses.append("group_id = ?")
        params.append(group_id)
    if source_language:
        clauses.append("source_language = ?")
        params.append(source_language)
    if target_language:
        clauses.append("target_language = ?")
        params.append(target_language)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with connect(config.resolved_database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT id, group_id, source_language, target_language, source_text, translated_text, note, created_at, updated_at
            FROM translation_cache_terms
            {where}
            ORDER BY source_language, target_language, source_text COLLATE NOCASE
            """,
            tuple(params),
        ).fetchall()
    return [translation_term_from_row(row) for row in rows]


def save_translation_term(
    group_id: int,
    source_language: str,
    target_language: str,
    source_text: str,
    translated_text: str,
    *,
    note: str = "",
    term_id: int | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> TranslationTerm:
    source_text = source_text.strip()
    translated_text = translated_text.strip()
    if not source_text:
        raise ValueError("source_text is required")
    if not translated_text:
        raise ValueError("translated_text is required")

    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        if term_id is None:
            cursor = connection.execute(
                """
                INSERT INTO translation_cache_terms(
                    group_id, source_language, target_language, source_text, translated_text, note, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_id, source_language, target_language, source_text) DO UPDATE SET
                    translated_text = excluded.translated_text,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                RETURNING id, group_id, source_language, target_language, source_text, translated_text, note, created_at, updated_at
                """,
                (group_id, source_language, target_language, source_text, translated_text, note.strip(), now, now),
            )
        else:
            cursor = connection.execute(
                """
                UPDATE translation_cache_terms
                SET group_id = ?,
                    source_language = ?,
                    target_language = ?,
                    source_text = ?,
                    translated_text = ?,
                    note = ?,
                    updated_at = ?
                WHERE id = ?
                RETURNING id, group_id, source_language, target_language, source_text, translated_text, note, created_at, updated_at
                """,
                (group_id, source_language, target_language, source_text, translated_text, note.strip(), now, term_id),
            )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"translation term not found: {term_id}")
    return translation_term_from_row(row)


def delete_translation_term(term_id: int, *, config: AppConfig = DEFAULT_CONFIG) -> bool:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        cursor = connection.execute("DELETE FROM translation_cache_terms WHERE id = ?", (term_id,))
    return cursor.rowcount > 0
