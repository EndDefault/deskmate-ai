from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .document import summarize_document
from .web_actions import open_site


@dataclass(frozen=True)
class AssistantResult:
    message: str
    action: str


def handle_prompt(prompt: str, document_path: str | None = None) -> AssistantResult:
    normalized = prompt.strip()
    if not normalized:
        return AssistantResult(message="명령을 입력해 주세요.", action="empty")

    if document_path and _looks_like_summary_request(normalized):
        summary = summarize_document(Path(document_path))
        return AssistantResult(message=summary, action="summarize_document")

    if _looks_like_open_site_request(normalized):
        opened_url = open_site(normalized)
        return AssistantResult(message=f"{opened_url} 사이트를 열게요.", action="open_site")

    return AssistantResult(
        message="아직은 사이트 열기와 문서 요약을 중심으로 도와줄 수 있어요.",
        action="fallback",
    )


def _looks_like_summary_request(prompt: str) -> bool:
    keywords = ("요약", "정리", "설명", "summarize", "summary")
    return any(keyword in prompt.lower() for keyword in keywords)


def _looks_like_open_site_request(prompt: str) -> bool:
    keywords = ("열어", "켜줘", "접속", "open")
    return any(keyword in prompt.lower() for keyword in keywords)
