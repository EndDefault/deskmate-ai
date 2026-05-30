from deskmate_ai.storage.models import (
    CachedResponse,
    KeywordCache,
    KeywordCacheCategory,
    Memo,
    TranslationCacheGroup,
    TranslationTerm,
)
from deskmate_ai.storage.sqlite.document_cache_repository import (
    get_cached_document_summary,
    save_document_summary,
)
from deskmate_ai.storage.sqlite.keyword_cache_repository import (
    delete_keyword_cache,
    find_keyword_cache_in_text,
    get_keyword_cache,
    get_keyword_cache_by_keyword,
    get_keyword_cache_category,
    list_keyword_cache_categories,
    list_keyword_caches,
    save_keyword_cache,
    save_keyword_cache_category,
)
from deskmate_ai.storage.sqlite.memo_repository import add_memo, list_recent_memos
from deskmate_ai.storage.sqlite.profile_repository import get_profile_value, set_profile_value
from deskmate_ai.storage.sqlite.response_cache_repository import (
    get_cached_response,
    get_similar_cached_response,
    save_cached_response,
)
from deskmate_ai.storage.sqlite.schema import initialize_database
from deskmate_ai.storage.sqlite.translation_cache_repository import (
    delete_translation_cache_group,
    delete_translation_term,
    get_translation_cache_group,
    list_translation_cache_groups,
    list_translation_terms,
    save_translation_cache_group,
    save_translation_term,
)
from deskmate_ai.storage.sqlite.utils import document_cache_key, normalize_prompt, stable_hash

__all__ = [
    "CachedResponse",
    "KeywordCache",
    "KeywordCacheCategory",
    "Memo",
    "TranslationCacheGroup",
    "TranslationTerm",
    "add_memo",
    "delete_keyword_cache",
    "delete_translation_cache_group",
    "delete_translation_term",
    "document_cache_key",
    "find_keyword_cache_in_text",
    "get_cached_document_summary",
    "get_cached_response",
    "get_keyword_cache",
    "get_keyword_cache_by_keyword",
    "get_keyword_cache_category",
    "get_profile_value",
    "get_similar_cached_response",
    "get_translation_cache_group",
    "initialize_database",
    "list_keyword_cache_categories",
    "list_keyword_caches",
    "list_recent_memos",
    "list_translation_cache_groups",
    "list_translation_terms",
    "normalize_prompt",
    "save_cached_response",
    "save_document_summary",
    "save_keyword_cache",
    "save_keyword_cache_category",
    "save_translation_cache_group",
    "save_translation_term",
    "set_profile_value",
    "stable_hash",
]
