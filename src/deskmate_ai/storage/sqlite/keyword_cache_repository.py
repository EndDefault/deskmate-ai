from __future__ import annotations

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.models import KeywordCache, KeywordCacheCategory
from deskmate_ai.storage.sqlite.connection import connect, utc_now
from deskmate_ai.storage.sqlite.schema import initialize_database
from deskmate_ai.storage.sqlite.utils import (
    keyword_cache_category_from_row,
    keyword_cache_from_row,
    normalize_prompt,
)


def list_keyword_cache_categories(*, config: AppConfig = DEFAULT_CONFIG) -> list[KeywordCacheCategory]:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, name, created_at, updated_at
            FROM keyword_cache_categories
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
    return [keyword_cache_category_from_row(row) for row in rows]


def get_keyword_cache_category(
    category_id: int,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> KeywordCacheCategory | None:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        row = connection.execute(
            """
            SELECT id, name, created_at, updated_at
            FROM keyword_cache_categories
            WHERE id = ?
            """,
            (category_id,),
        ).fetchone()
    return None if row is None else keyword_cache_category_from_row(row)


def save_keyword_cache_category(
    name: str,
    *,
    category_id: int | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> KeywordCacheCategory:
    name = name.strip()
    if not name:
        raise ValueError("name is required")

    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        if category_id is None:
            cursor = connection.execute(
                """
                INSERT INTO keyword_cache_categories(name, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET updated_at = excluded.updated_at
                RETURNING id, name, created_at, updated_at
                """,
                (name, now, now),
            )
        else:
            cursor = connection.execute(
                """
                UPDATE keyword_cache_categories
                SET name = ?,
                    updated_at = ?
                WHERE id = ?
                RETURNING id, name, created_at, updated_at
                """,
                (name, now, category_id),
            )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"keyword cache category not found: {category_id}")
    return keyword_cache_category_from_row(row)


def list_keyword_caches(
    *,
    category_id: int | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> list[KeywordCache]:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        if category_id is None:
            rows = connection.execute(
                """
                SELECT id, category_id, keyword, action_type, content, created_at, updated_at
                FROM keyword_cache
                ORDER BY keyword COLLATE NOCASE
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, category_id, keyword, action_type, content, created_at, updated_at
                FROM keyword_cache
                WHERE category_id = ?
                ORDER BY keyword COLLATE NOCASE
                """,
                (category_id,),
            ).fetchall()
    return [keyword_cache_from_row(row) for row in rows]


def get_keyword_cache(cache_id: int, *, config: AppConfig = DEFAULT_CONFIG) -> KeywordCache | None:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        row = connection.execute(
            """
            SELECT id, category_id, keyword, action_type, content, created_at, updated_at
            FROM keyword_cache
            WHERE id = ?
            """,
            (cache_id,),
        ).fetchone()
    return None if row is None else keyword_cache_from_row(row)


def get_keyword_cache_by_keyword(
    keyword: str,
    *,
    category_ids: list[int] | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> KeywordCache | None:
    normalized = normalize_prompt(keyword)
    if not normalized:
        return None

    initialize_database(config=config)
    params: list[object] = [normalized]
    category_clause = ""
    if category_ids:
        placeholders = ", ".join("?" for _ in category_ids)
        category_clause = f" AND category_id IN ({placeholders})"
        params.extend(category_ids)
    with connect(config.resolved_database_path) as connection:
        row = connection.execute(
            f"""
            SELECT id, category_id, keyword, action_type, content, created_at, updated_at
            FROM keyword_cache
            WHERE keyword_normalized = ?{category_clause}
            ORDER BY length(keyword_normalized) DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    return None if row is None else keyword_cache_from_row(row)


def find_keyword_cache_in_text(
    text: str,
    *,
    category_ids: list[int] | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> KeywordCache | None:
    normalized = normalize_prompt(text)
    if not normalized:
        return None

    if category_ids:
        caches = [
            cache
            for category_id in category_ids
            for cache in list_keyword_caches(category_id=category_id, config=config)
        ]
    else:
        caches = list_keyword_caches(config=config)

    matches = [
        cache
        for cache in caches
        if normalize_prompt(cache.keyword) and normalize_prompt(cache.keyword) in normalized
    ]
    if not matches:
        return None
    return max(matches, key=lambda cache: len(normalize_prompt(cache.keyword)))


def save_keyword_cache(
    keyword: str,
    content: str,
    *,
    category_id: int = 1,
    action_type: str = "show_text",
    cache_id: int | None = None,
    config: AppConfig = DEFAULT_CONFIG,
) -> KeywordCache:
    keyword = keyword.strip()
    content = content.strip()
    if not keyword:
        raise ValueError("keyword is required")
    if not content:
        raise ValueError("content is required")
    if action_type not in {"show_text", "open_url", "translate"}:
        raise ValueError(f"unsupported action type: {action_type}")

    initialize_database(config=config)
    now = utc_now()
    normalized = normalize_prompt(keyword)
    with connect(config.resolved_database_path) as connection:
        if cache_id is None:
            cursor = connection.execute(
                """
                INSERT INTO keyword_cache(
                    category_id,
                    keyword,
                    keyword_normalized,
                    action_type,
                    content,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(category_id, keyword_normalized) DO UPDATE SET
                    keyword = excluded.keyword,
                    action_type = excluded.action_type,
                    content = excluded.content,
                    updated_at = excluded.updated_at
                RETURNING id, category_id, keyword, action_type, content, created_at, updated_at
                """,
                (category_id, keyword, normalized, action_type, content, now, now),
            )
        else:
            cursor = connection.execute(
                """
                UPDATE keyword_cache
                SET category_id = ?,
                    keyword = ?,
                    keyword_normalized = ?,
                    action_type = ?,
                    content = ?,
                    updated_at = ?
                WHERE id = ?
                RETURNING id, category_id, keyword, action_type, content, created_at, updated_at
                """,
                (category_id, keyword, normalized, action_type, content, now, cache_id),
            )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"keyword cache not found: {cache_id}")
    return keyword_cache_from_row(row)


def delete_keyword_cache(cache_id: int, *, config: AppConfig = DEFAULT_CONFIG) -> bool:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        cursor = connection.execute("DELETE FROM keyword_cache WHERE id = ?", (cache_id,))
    return cursor.rowcount > 0

