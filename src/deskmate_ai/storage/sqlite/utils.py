from __future__ import annotations

import sqlite3
from hashlib import sha256

from deskmate_ai.storage.models import KeywordCache, KeywordCacheCategory


def normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.casefold().split())


def stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def document_cache_key(file_hash: str, max_chars: int) -> str:
    return stable_hash(f"document-summary:{file_hash}:{max_chars}")


def token_set(prompt: str) -> set[str]:
    return {token for token in prompt.split() if token}


def jaccard_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def keyword_cache_category_from_row(row: sqlite3.Row) -> KeywordCacheCategory:
    return KeywordCacheCategory(
        id=int(row["id"]),
        name=str(row["name"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def keyword_cache_from_row(row: sqlite3.Row) -> KeywordCache:
    return KeywordCache(
        id=int(row["id"]),
        category_id=int(row["category_id"]),
        keyword=str(row["keyword"]),
        action_type=str(row["action_type"]),
        content=str(row["content"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
