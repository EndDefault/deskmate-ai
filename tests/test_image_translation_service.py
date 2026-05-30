from pathlib import Path

from deskmate_ai.services.image_translation_service import (
    ImageTranslationSettings,
    collect_image_paths,
    estimate_total_steps,
    run_image_translation_preview,
)


def test_collect_image_paths_reads_files_and_folders(tmp_path: Path) -> None:
    image = tmp_path / "page.jpg"
    nested = tmp_path / "nested.png"
    ignored = tmp_path / "note.txt"
    image.write_bytes(b"fake")
    nested.write_bytes(b"fake")
    ignored.write_text("ignore", encoding="utf-8")

    paths = collect_image_paths([image, tmp_path])

    assert paths == [image, nested]


def test_run_image_translation_preview_reports_progress(tmp_path: Path) -> None:
    image = tmp_path / "page.jpg"
    image.write_bytes(b"fake")
    settings = ImageTranslationSettings(
        source_language="ja",
        target_language="ko",
        ocr_passes=3,
        upscale_factor=2,
        enhance_contrast=True,
        grayscale=True,
        min_confidence=0.55,
        cache_group_name="일본어 캐시",
    )

    progress = list(run_image_translation_preview([image], settings))

    assert len(progress) == estimate_total_steps(1, settings)
    assert progress[0].stage == "이미지 로딩"
    assert progress[-1].ratio == 1.0
