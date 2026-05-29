from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from pypdf import PdfReader

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.services.storage_service import get_cached_document_summary, save_document_summary


def summarize_document(
    path: Path,
    max_chars: int = 1200,
    *,
    config: AppConfig = DEFAULT_CONFIG,
    use_cache: bool = True,
) -> str:
    file_hash = hash_file(path)
    if use_cache:
        cached = get_cached_document_summary(path, file_hash, max_chars, config=config)
        if cached:
            return cached

    text = extract_text(path)
    if not text:
        summary = "문서에서 읽을 수 있는 텍스트를 찾지 못했어요."
        save_document_summary(path, file_hash, max_chars, summary, config=config)
        return summary

    compact = " ".join(text.split())
    preview = compact[:max_chars]
    summary = f"문서 핵심 내용 미리보기:\n{preview}"
    save_document_summary(path, file_hash, max_chars, summary, config=config)
    return summary


def extract_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"아직 지원하지 않는 파일 형식입니다: {suffix}")


def hash_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)
