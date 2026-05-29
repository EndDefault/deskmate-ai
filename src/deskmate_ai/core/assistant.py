from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.services.document_service import summarize_document
from deskmate_ai.services.llm_service import ask_local_model
from deskmate_ai.services.storage_service import (
    add_memo,
    get_cached_response,
    get_profile_value,
    get_similar_cached_response,
    list_recent_memos,
    save_cached_response,
    set_profile_value,
    stable_hash,
)
from deskmate_ai.services.web_service import open_site


@dataclass(frozen=True)
class AssistantResult:
    message: str
    action: str


def handle_prompt(
    prompt: str,
    document_path: str | None = None,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> AssistantResult:
    normalized = prompt.strip()
    if not normalized:
        return AssistantResult(message="명령을 입력해 주세요.", action="empty")

    routed = _handle_local_request(normalized, config=config)
    if routed is not None:
        return routed

    if document_path and _looks_like_summary_request(normalized):
        summary = summarize_document(
            Path(document_path),
            max_chars=config.document_preview_chars,
            config=config,
        )
        return AssistantResult(message=summary, action="summarize_document")

    if _looks_like_open_site_request(normalized):
        opened_url = open_site(normalized)
        return AssistantResult(message=f"{opened_url} 사이트를 열게요.", action="open_site")

    options_hash = _llm_options_hash(config)
    cached = get_cached_response(
        normalized,
        model=config.ollama_model,
        options_hash=options_hash,
        config=config,
    )
    if cached:
        return AssistantResult(message=cached, action="cached_response")

    similar = get_similar_cached_response(
        normalized,
        model=config.ollama_model,
        options_hash=options_hash,
        config=config,
    )
    if similar:
        return AssistantResult(message=similar.response, action="similar_cached_response")

    answer = ask_local_model(normalized, config=config)
    if answer:
        save_cached_response(
            normalized,
            answer,
            model=config.ollama_model,
            options_hash=options_hash,
            config=config,
        )
        return AssistantResult(message=answer, action="ask_local_model")

    return AssistantResult(
        message="아직은 사이트 열기, 문서 요약, 로컬 AI 응답을 중심으로 지원해요.",
        action="fallback",
    )


def _looks_like_summary_request(prompt: str) -> bool:
    keywords = ("요약", "정리", "설명", "summarize", "summary")
    return any(keyword in prompt.lower() for keyword in keywords)


def _looks_like_open_site_request(prompt: str) -> bool:
    keywords = ("열어", "켜줘", "접속", "open")
    return any(keyword in prompt.lower() for keyword in keywords)


def _handle_local_request(prompt: str, *, config: AppConfig) -> AssistantResult | None:
    lower = prompt.lower()

    memo_prefixes = ("기억해", "메모해", "remember ", "memo ")
    for prefix in memo_prefixes:
        if lower.startswith(prefix):
            content = prompt[len(prefix) :].strip(" :->")
            if not content:
                return AssistantResult(message="기억할 내용을 같이 적어주세요.", action="memo_missing")
            memo = add_memo(content, config=config)
            return AssistantResult(message=f"메모 {memo.id}번으로 기억해둘게요.", action="add_memo")

    if any(keyword in lower for keyword in ("최근 메모", "메모 보여", "show memos", "recent memos")):
        memos = list_recent_memos(config=config)
        if not memos:
            return AssistantResult(message="아직 저장된 메모가 없어요.", action="list_memos")
        lines = [f"{memo.id}. {memo.content}" for memo in memos]
        return AssistantResult(message="최근 메모:\n" + "\n".join(lines), action="list_memos")

    name_markers = ("내 이름은", "my name is ")
    for marker in name_markers:
        if lower.startswith(marker):
            name = prompt[len(marker) :].strip(" .:->")
            if not name:
                return AssistantResult(message="이름을 같이 알려주세요.", action="profile_missing")
            set_profile_value("name", name, config=config)
            return AssistantResult(message=f"좋아요. 앞으로 {name}님으로 기억할게요.", action="set_profile")

    if any(keyword in lower for keyword in ("내 이름 뭐", "내 이름이 뭐", "what is my name")):
        name = get_profile_value("name", config=config)
        if name:
            return AssistantResult(message=f"{name}님으로 기억하고 있어요.", action="get_profile")
        return AssistantResult(message="아직 이름을 기억하지 못했어요.", action="get_profile")

    return None


def _llm_options_hash(config: AppConfig) -> str:
    return stable_hash(
        "|".join(
            [
                config.ollama_keep_alive,
                str(config.ollama_max_tokens),
                str(config.ollama_timeout_seconds),
            ]
        )
    )
