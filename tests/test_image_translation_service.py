from pathlib import Path

from deskmate_ai.services import image_translation_service as service
from deskmate_ai.storage.models import TranslationCacheGroup, TranslationTerm
from deskmate_ai.services.image_translation_service import (
    ImageTranslationSettings,
    OcrReviewResult,
    OcrTextBox,
    add_manual_ocr_box,
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


def test_add_manual_ocr_box_updates_review(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "page.jpg"
    image.write_bytes(b"fake")
    review = OcrReviewResult(image_path=image, image=object(), boxes=[], preview_path=tmp_path / "old.png")
    monkeypatch.setattr(service, "_render_ocr_review_image", lambda *_: tmp_path / "new.png")

    updated = add_manual_ocr_box(
        review,
        make_settings(),
        text=" AH, HELLO ",
        left=10,
        top=20,
        width=30,
        height=40,
    )

    assert updated.preview_path == tmp_path / "new.png"
    assert updated.boxes == [OcrTextBox("AH, HELLO", left=10, top=20, width=30, height=40, confidence=1.0)]


def test_delete_ocr_box_updates_review(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "page.jpg"
    image.write_bytes(b"fake")
    review = OcrReviewResult(
        image_path=image,
        image=object(),
        boxes=[
            OcrTextBox("keep", left=1, top=1, width=10, height=10, confidence=0.8),
            OcrTextBox("remove", left=20, top=1, width=10, height=10, confidence=0.8),
        ],
        preview_path=tmp_path / "old.png",
    )
    monkeypatch.setattr(service, "_render_ocr_review_image", lambda *_: tmp_path / "new.png")

    updated = service.delete_ocr_box(review, make_settings(), index=1)

    assert updated.preview_path == tmp_path / "new.png"
    assert [box.text for box in updated.boxes] == ["keep"]


def test_split_words_by_horizontal_gap_separates_panels() -> None:
    words = [
        ("left", 10, 10, 20, 10, 0.9),
        ("panel", 35, 10, 30, 10, 0.9),
        ("right", 180, 10, 30, 10, 0.9),
    ]

    segments = service._split_words_by_horizontal_gap(words)

    assert [[word[0] for word in segment] for segment in segments] == [["left", "panel"], ["right"]]


def test_translate_boxes_uses_translation_cache_before_model(monkeypatch) -> None:
    settings = make_settings()
    monkeypatch.setattr(
        service,
        "list_translation_cache_groups",
        lambda **_kwargs: [TranslationCacheGroup(1, "영어 캐시", "en", "ko", "", "")],
    )
    monkeypatch.setattr(
        service,
        "list_translation_terms",
        lambda **_kwargs: [TranslationTerm(1, 1, "en", "ko", "thank you. head over around", "고마워. 근처로 와.", "", "", "")],
    )
    monkeypatch.setattr(service, "ask_local_model", lambda *_args, **_kwargs: "1|모델 번역")

    result = service._translate_boxes(
        [OcrTextBox("thank you. head over around", left=0, top=0, width=20, height=10, confidence=0.9)],
        settings,
        config=object(),
    )

    assert result[0][1] == "고마워. 근처로 와."


def test_translate_text_uses_partial_cache_as_prompt_hints(monkeypatch) -> None:
    captured = {}

    def fake_model(prompt, **_kwargs):
        captured["prompt"] = prompt
        return "밤 10시쯤, 공원 뒤편 벤치 근처."

    monkeypatch.setattr(service, "ask_local_model", fake_model)

    result = service._translate_text(
        "Around 10 PM, at the back of Sakura Park, near a bench.",
        make_settings(),
        config=object(),
        cache={
            "around 10 pm": "밤 10시쯤",
            "at the back of": "뒤편",
            "near a bench": "벤치 근처",
        },
    )

    assert result == "밤 10시쯤, 공원 뒤편 벤치 근처."
    assert "Translation hints from cache" in captured["prompt"]
    assert "- around 10 pm = 밤 10시쯤" in captured["prompt"]
    assert "- at the back of = 뒤편" in captured["prompt"]
    assert "- near a bench = 벤치 근처" in captured["prompt"]


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


def test_translate_text_prompt_uses_selected_target_language(monkeypatch) -> None:
    captured = {}

    def fake_model(prompt, **_kwargs):
        captured["prompt"] = prompt
        return "안녕하세요"

    monkeypatch.setattr(service, "ask_local_model", fake_model)

    result = service._translate_text("Hello", make_settings(), config=object())

    assert result == "안녕하세요"
    assert "into Korean" in captured["prompt"]
    assert "Korean Hangul" in captured["prompt"]
