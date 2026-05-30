from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Memo:
    id: int
    content: str
    created_at: str


@dataclass(frozen=True)
class CachedResponse:
    response: str
    score: float = 1.0


@dataclass(frozen=True)
class KeywordCacheCategory:
    id: int
    name: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class KeywordCache:
    id: int
    category_id: int
    keyword: str
    action_type: str
    content: str
    created_at: str
    updated_at: str
