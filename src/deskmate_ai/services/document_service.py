from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def summarize_document(path: Path, max_chars: int = 1200) -> str:
    text = extract_text(path)
    if not text:
        return "문서에서 읽을 수 있는 텍스트를 찾지 못했어요."

    compact = " ".join(text.split())
    preview = compact[:max_chars]
    return f"문서 핵심 내용 미리보기:\n{preview}"


def extract_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"아직 지원하지 않는 파일 형식입니다: {suffix}")


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)
