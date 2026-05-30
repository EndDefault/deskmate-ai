from pathlib import Path

from deskmate_ai.services import image_translation_service as service
from deskmate_ai.services.image_translation_service import (
    ImageTranslationSettings,
    OcrTextBox,
    collect_image_paths,
    estimate_total_steps,
    run_image_translation,
    run_image_translation_preview,
)


def make_settings() -> ImageTranslationSettings:
    return ImageTranslationSettings(
        source_language="en",
        target_language="ko",
        ocr_passes=1,
        upscale_factor=1,
        enhance_contrast=False,
        grayscale=False,
        min_confidence=0.55,
        cache_group_names=["영어 캐시"],
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
        source_language="en",
        target_language="ko",
        ocr_passes=3,
        upscale_factor=2,
        enhance_contrast=True,
        grayscale=True,
        min_confidence=0.55,
        cache_group_names=["일본어 캐시"],
    )

    progress = list(run_image_translation_preview([image], settings))

    assert len(progress) == estimate_total_steps(1, settings)
    assert progress[0].stage == "이미지 로딩"
    assert progress[-1].ratio == 1.0


def test_run_image_translation_saves_output_with_mocked_pipeline(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "page.jpg"
    output = tmp_path / "translated" / "page_translated.png"
    image.write_bytes(b"fake")
    settings = ImageTranslationSettings(
        source_language="en",
        target_language="ko",
        ocr_passes=1,
        upscale_factor=1,
        enhance_contrast=False,
        grayscale=False,
        min_confidence=0.55,
        cache_group_names=["영어 캐시"],
        output_dir=tmp_path / "translated",
    )

    monkeypatch.setattr(service, "_load_and_preprocess_image", lambda *_: object())
    monkeypatch.setattr(
        service,
        "_extract_text_boxes",
        lambda *_: [OcrTextBox("hello", left=1, top=1, width=20, height=10, confidence=0.9)],
    )
    monkeypatch.setattr(service, "_translate_text", lambda text, *_args, **_kwargs: "안녕")
    monkeypatch.setattr(service, "_render_translated_image", lambda *_: output)

    progress = list(run_image_translation([image], settings))

    assert progress[-1].stage == "결과 저장"
    assert progress[-1].output_path == output


def test_translate_texts_parses_pipe_numbered_batch(monkeypatch) -> None:
    monkeypatch.setattr(service, "ask_local_model", lambda *_args, **_kwargs: "1|안녕하세요\n2|좋은 저녁입니다")

    result = service._translate_texts(["Hello", "Good evening"], make_settings(), config=object())

    assert result == ["안녕하세요", "좋은 저녁입니다"]


def test_translate_texts_falls_back_per_missing_item(monkeypatch) -> None:
    monkeypatch.setattr(service, "ask_local_model", lambda *_args, **_kwargs: "1. 안녕하세요")
    monkeypatch.setattr(service, "_translate_text", lambda text, *_args, **_kwargs: f"개별 번역: {text}")

    result = service._translate_texts(["Hello", "Good evening"], make_settings(), config=object())

    assert result == ["안녕하세요", "개별 번역: Good evening"]


def test_translate_texts_falls_back_to_individual_when_batch_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(service, "ask_local_model", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(service, "_translate_text", lambda text, *_args, **_kwargs: f"개별 번역: {text}")

    result = service._translate_texts(["Hello", "Good evening"], make_settings(), config=object())

    assert result == ["개별 번역: Hello", "개별 번역: Good evening"]
