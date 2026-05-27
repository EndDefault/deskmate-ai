from pathlib import Path

from deskmate_ai.services.document_service import extract_text, summarize_document


def test_extract_text_reads_text_file(tmp_path: Path) -> None:
    document = tmp_path / "note.txt"
    document.write_text("hello deskmate", encoding="utf-8")

    assert extract_text(document) == "hello deskmate"


def test_summarize_document_compacts_text(tmp_path: Path) -> None:
    document = tmp_path / "note.md"
    document.write_text("first\n\nsecond", encoding="utf-8")

    summary = summarize_document(document)

    assert "문서 핵심 내용" in summary
    assert "first second" in summary
