from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.services.document_service import summarize_document
from deskmate_ai.services.llm_service import ask_local_model
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

    if document_path and _looks_like_summary_request(normalized):
        summary = summarize_document(Path(document_path), max_chars=config.document_preview_chars)
        return AssistantResult(message=summary, action="summarize_document")

    if _looks_like_open_site_request(normalized):
        opened_url = open_site(normalized)
        return AssistantResult(message=f"{opened_url} 사이트를 열게요.", action="open_site")

    answer = ask_local_model(normalized, config=config)
    if answer:
        return AssistantResult(message=answer, action="ask_local_model")

    return AssistantResult(
        message="아직은 사이트 열기, 문서 요약, 로컬 AI 답변을 중심으로 지원해요.",
        action="fallback",
    )


def _looks_like_summary_request(prompt: str) -> bool:
    keywords = ("요약", "정리", "설명", "summarize", "summary")
    return any(keyword in prompt.lower() for keyword in keywords)


def _looks_like_open_site_request(prompt: str) -> bool:
    keywords = ("열어", "켜줘", "접속", "open")
    return any(keyword in prompt.lower() for keyword in keywords)
