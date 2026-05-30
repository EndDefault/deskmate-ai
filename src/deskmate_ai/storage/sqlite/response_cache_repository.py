from __future__ import annotations

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.models import CachedResponse
from deskmate_ai.storage.sqlite.connection import connect, utc_now
from deskmate_ai.storage.sqlite.schema import initialize_database
from deskmate_ai.storage.sqlite.utils import jaccard_score, normalize_prompt, stable_hash, token_set


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
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        if model is None and options_hash is None:
            row = connection.execute("SELECT response FROM response_cache WHERE prompt = ?", (normalized,)).fetchone()
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
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
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
            (normalized, response.strip(), now, stable_hash(normalized), model, options_hash, expires_at),
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
    tokens = token_set(normalized)
    if len(tokens) < 2:
        return None

    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
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
            score = jaccard_score(tokens, token_set(str(row["prompt"])))
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
