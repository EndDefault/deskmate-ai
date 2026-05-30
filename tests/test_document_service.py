from pathlib import Path

from deskmate_ai.config import AppConfig
from deskmate_ai.services.document_service import extract_text, hash_file, summarize_document


def test_extract_text_reads_text_file(tmp_path: Path) -> None:
    document = tmp_path / "note.txt"
    document.write_text("hello deskmate", encoding="utf-8")

    assert extract_text(document) == "hello deskmate"


def test_summarize_document_compacts_text(tmp_path: Path) -> None:
    document = tmp_path / "note.md"
    document.write_text("first\n\nsecond", encoding="utf-8")
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    summary = summarize_document(document, config=config)

    assert "문서 핵심 내용" in summary
    assert "first second" in summary


def test_summarize_document_reuses_file_hash_cache(tmp_path: Path) -> None:
    original = tmp_path / "original.md"
    copied = tmp_path / "copied.md"
    content = "same document body"
    original.write_text(content, encoding="utf-8")
    copied.write_text(content, encoding="utf-8")
    config = AppConfig(database_path=tmp_path / "deskmate.db")

    first = summarize_document(original, config=config)
    second = summarize_document(copied, config=config)

    assert hash_file(original) == hash_file(copied)
    assert second == first
