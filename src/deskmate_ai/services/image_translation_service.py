from __future__ import annotations

import re
import shutil
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib import error, parse, request
import json

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.services.ai import ask_local_model


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
TESSERACT_LANGUAGES = {
    "en": "eng",
    "ja": "jpn",
    "ko": "kor",
}


@dataclass(frozen=True)
class ImageTranslationSettings:
    source_language: str
    target_language: str
    ocr_passes: int
    upscale_factor: int
    enhance_contrast: bool
    grayscale: bool
    min_confidence: float
    cache_group_names: list[str]
    output_dir: Path | None = None
    translation_provider: str = "local"


@dataclass(frozen=True)
class ImageTranslationProgress:
    current: int
    total: int
    stage: str
    message: str
    output_path: Path | None = None

    @property
    def ratio(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.current / self.total))


@dataclass(frozen=True)
class OcrTextBox:
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float


@dataclass(frozen=True)
class OcrReviewResult:
    image_path: Path
    image: object
    boxes: list[OcrTextBox]
    preview_path: Path


@dataclass(frozen=True)
class TranslationReviewResult:
    image_path: Path
    preview_path: Path
    final_path: Path
    translations: list[tuple[OcrTextBox, str]]


def collect_image_paths(paths: Iterable[str | Path]) -> list[Path]:
    images: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            images.extend(
                child
                for child in sorted(path.iterdir())
                if child.is_file() and child.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
            images.append(path)
    return _dedupe_paths(images)


def estimate_total_steps(image_count: int, settings: ImageTranslationSettings) -> int:
    if image_count <= 0:
        return 0
    per_image_steps = 2 + max(1, settings.ocr_passes) + 2
    return image_count * per_image_steps


def prepare_ocr_review(image_path: Path, settings: ImageTranslationSettings) -> OcrReviewResult:
    working_image = _load_and_preprocess_image(image_path, settings)
    text_boxes = _extract_text_boxes(working_image, settings)
    preview_path = _render_ocr_review_image(image_path, working_image, text_boxes, settings)
    return OcrReviewResult(image_path=image_path, image=working_image, boxes=text_boxes, preview_path=preview_path)


def prepare_translation_review(
    review: OcrReviewResult,
    settings: ImageTranslationSettings,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> TranslationReviewResult:
    translations = _translate_boxes(review.boxes, settings, config=config)
    preview_path = _render_translated_image(
        review.image_path,
        review.image,
        translations,
        settings,
        suffix="_translation_review",
    )
    final_path = _output_path(review.image_path, settings, suffix="_translated")
    return TranslationReviewResult(
        image_path=review.image_path,
        preview_path=preview_path,
        final_path=final_path,
        translations=translations,
    )


def approve_translation_review(review: TranslationReviewResult) -> Path:
    review.final_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(review.preview_path, review.final_path)
    return review.final_path


def format_ocr_review_text(boxes: list[OcrTextBox]) -> str:
    if not boxes:
        return "OCR로 감지한 텍스트가 없습니다."
    lines: list[str] = []
    for index, box in enumerate(boxes, start=1):
        lines.append(
            f"{index}. [{box.confidence:.0%}] ({box.left}, {box.top}, {box.width}x{box.height}) {box.text}"
        )
    return "\n".join(lines)


def format_translation_review_text(translations: list[tuple[OcrTextBox, str]]) -> str:
    if not translations:
        return "번역할 텍스트가 없습니다."
    lines: list[str] = []
    for index, (box, translated_text) in enumerate(translations, start=1):
        lines.append(f"{index}. 원문: {box.text}\n   번역: {translated_text}")
    return "\n".join(lines)


def run_image_translation(
    image_paths: list[Path],
    settings: ImageTranslationSettings,
    *,
    config: AppConfig = DEFAULT_CONFIG,
    should_cancel: Callable[[], bool] | None = None,
) -> Iterable[ImageTranslationProgress]:
    total = estimate_total_steps(len(image_paths), settings)
    current = 0
    if total == 0:
        yield ImageTranslationProgress(0, 0, "대기", "처리할 이미지가 없습니다.")
        return

    for image_path in image_paths:
        if _is_cancelled(should_cancel):
            yield ImageTranslationProgress(current, total, "취소", "작업을 취소했습니다.")
            return

        current += 1
        yield ImageTranslationProgress(current, total, "이미지 로딩", image_path.name)

        try:
            working_image = _load_and_preprocess_image(image_path, settings)
        except RuntimeError as exc:
            yield ImageTranslationProgress(current, total, "오류", str(exc))
            continue

        current += 1
        yield ImageTranslationProgress(current, total, "전처리", f"{image_path.name}: {_describe_preprocessing(settings)}")

        text_boxes: list[OcrTextBox] = []
        for pass_index in range(1, max(1, settings.ocr_passes) + 1):
            if _is_cancelled(should_cancel):
                yield ImageTranslationProgress(current, total, "취소", "작업을 취소했습니다.")
                return
            if pass_index == max(1, settings.ocr_passes):
                try:
                    text_boxes = _extract_text_boxes(working_image, settings)
                except RuntimeError as exc:
                    yield ImageTranslationProgress(current, total, "오류", str(exc))
                    break
            current += 1
            yield ImageTranslationProgress(
                current,
                total,
                "OCR",
                f"{image_path.name}: OCR {pass_index}/{settings.ocr_passes}회",
            )

        if _is_cancelled(should_cancel):
            yield ImageTranslationProgress(current, total, "취소", "작업을 취소했습니다.")
            return

        yield ImageTranslationProgress(
            current,
            total,
            "번역 요청",
            f"{image_path.name}: {len(text_boxes)}개 줄을 한 번에 번역 중",
        )
        current += 1
        translations = _translate_boxes(text_boxes, settings, config=config)
        translated_count = sum(
            1
            for box, translated_text in translations
            if _normalize_translation_text(translated_text) != _normalize_translation_text(box.text)
        )
        yield ImageTranslationProgress(
            current,
            total,
            "번역",
            f"{image_path.name}: {translated_count}/{len(translations)}개 텍스트 변환",
        )

        if _is_cancelled(should_cancel):
            yield ImageTranslationProgress(current, total, "취소", "작업을 취소했습니다.")
            return

        current += 1
        output_path = _render_translated_image(image_path, working_image, translations, settings)
        yield ImageTranslationProgress(
            current,
            total,
            "결과 저장",
            f"{image_path.name}: {output_path}",
            output_path=output_path,
        )


def run_image_translation_preview(
    image_paths: list[Path],
    settings: ImageTranslationSettings,
) -> Iterable[ImageTranslationProgress]:
    total = estimate_total_steps(len(image_paths), settings)
    current = 0
    if total == 0:
        yield ImageTranslationProgress(0, 0, "대기", "처리할 이미지가 없습니다.")
        return

    for image_path in image_paths:
        current += 1
        yield ImageTranslationProgress(current, total, "이미지 로딩", image_path.name)

        current += 1
        yield ImageTranslationProgress(current, total, "전처리", f"{image_path.name}: {_describe_preprocessing(settings)}")

        for pass_index in range(1, max(1, settings.ocr_passes) + 1):
            current += 1
            yield ImageTranslationProgress(
                current,
                total,
                "OCR",
                f"{image_path.name}: OCR {pass_index}/{settings.ocr_passes}회",
            )

        current += 1
        yield ImageTranslationProgress(
            current,
            total,
            "번역",
            f"{image_path.name}: {settings.source_language}->{settings.target_language}, {', '.join(settings.cache_group_names)}",
        )

        current += 1
        yield ImageTranslationProgress(current, total, "결과 정리", f"{image_path.name}: 미리보기 완료")


def _load_and_preprocess_image(image_path: Path, settings: ImageTranslationSettings):
    try:
        from PIL import Image, ImageEnhance, ImageOps
    except ImportError as exc:
        raise RuntimeError("Pillow가 설치되어 있지 않습니다. pip install -e . 명령으로 의존성을 다시 설치해 주세요.") from exc

    image = Image.open(image_path).convert("RGB")
    if settings.upscale_factor > 1:
        image = image.resize(
            (image.width * settings.upscale_factor, image.height * settings.upscale_factor),
            Image.Resampling.LANCZOS,
        )
    if settings.grayscale:
        image = ImageOps.grayscale(image).convert("RGB")
    if settings.enhance_contrast:
        image = ImageEnhance.Contrast(image).enhance(1.8)
    return image


def _extract_text_boxes(image, settings: ImageTranslationSettings) -> list[OcrTextBox]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("pytesseract가 설치되어 있지 않습니다. pip install -e . 명령으로 의존성을 다시 설치해 주세요.") from exc

    try:
        data = pytesseract.image_to_data(
            image,
            lang=TESSERACT_LANGUAGES.get(settings.source_language, "eng"),
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract 실행 파일을 찾을 수 없습니다. Tesseract OCR을 설치한 뒤 다시 실행해 주세요.") from exc

    min_confidence = settings.min_confidence * 100
    grouped: dict[tuple[int, int, int], list[tuple[str, int, int, int, int, float]]] = defaultdict(list)
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            continue
        if confidence < min_confidence:
            continue
        key = (
            int(data.get("block_num", [0])[index]),
            int(data.get("par_num", [0])[index]),
            int(data.get("line_num", [0])[index]),
        )
        grouped[key].append(
            (
                text,
                int(data["left"][index]),
                int(data["top"][index]),
                int(data["width"][index]),
                int(data["height"][index]),
                confidence / 100,
            )
        )

    boxes: list[OcrTextBox] = []
    for words in grouped.values():
        words.sort(key=lambda item: item[1])
        text = " ".join(word[0] for word in words)
        left = min(word[1] for word in words)
        top = min(word[2] for word in words)
        right = max(word[1] + word[3] for word in words)
        bottom = max(word[2] + word[4] for word in words)
        confidence = sum(word[5] for word in words) / len(words)
        boxes.append(OcrTextBox(text=text, left=left, top=top, width=right - left, height=bottom - top, confidence=confidence))
    return sorted(boxes, key=lambda box: (box.top, box.left))


def _translate_boxes(
    boxes: list[OcrTextBox],
    settings: ImageTranslationSettings,
    *,
    config: AppConfig,
) -> list[tuple[OcrTextBox, str]]:
    if settings.source_language == settings.target_language:
        return [(box, box.text) for box in boxes]

    unique_texts = list(dict.fromkeys(box.text for box in boxes))
    translated_texts = _translate_texts(unique_texts, settings, config=config)
    cache = dict(zip(unique_texts, translated_texts, strict=False))
    return [(box, cache.get(box.text, box.text)) for box in boxes]


def _translate_texts(texts: list[str], settings: ImageTranslationSettings, *, config: AppConfig) -> list[str]:
    if not texts:
        return []
    if len(texts) == 1:
        return [_translate_text(texts[0], settings, config=config)]

    if settings.translation_provider == "deepl":
        deepl_translations = _translate_texts_with_deepl(texts, settings, config=config)
        if deepl_translations:
            return deepl_translations

    numbered_lines = "\n".join(f"{index + 1}|{text}" for index, text in enumerate(texts))
    prompt = (
        "Translate each numbered item. "
        f"Source language: {settings.source_language}. "
        f"Target language: {settings.target_language}. "
        "Return exactly one line per input in this format: number|translated text. "
        "Keep names, IDs, numbers, and symbols as needed, but translate natural-language sentences. "
        "If text is explicit or adult, translate it neutrally without censoring. "
        "Do not add explanations.\n\n"
        f"{numbered_lines}"
    )
    translated = ask_local_model(prompt, config=config)
    parsed = _parse_numbered_translation_map(translated or "")
    if not parsed:
        return [_translate_text(text, settings, config=config) for text in texts]

    results: list[str] = []
    for index, source_text in enumerate(texts, start=1):
        translated_text = parsed.get(index)
        if translated_text:
            results.append(translated_text)
            continue
        results.append(_translate_text(source_text, settings, config=config))
    return results


def _translate_text(text: str, settings: ImageTranslationSettings, *, config: AppConfig) -> str:
    if settings.source_language == settings.target_language:
        return text
    if settings.translation_provider == "deepl":
        translated_texts = _translate_texts_with_deepl([text], settings, config=config)
        if translated_texts:
            return translated_texts[0]
    prompt = (
        "Translate the following text. "
        f"Source language: {settings.source_language}. "
        f"Target language: {settings.target_language}. "
        "Return only the translated text, with no explanation.\n\n"
        f"{text}"
    )
    translated = ask_local_model(prompt, config=config)
    return translated or text


def _translate_texts_with_deepl(
    texts: list[str],
    settings: ImageTranslationSettings,
    *,
    config: AppConfig,
) -> list[str] | None:
    api_key = config.deepl_api_key.strip()
    if not api_key or not api_key.endswith(":fx"):
        return None

    source_language = _deepl_language(settings.source_language)
    target_language = _deepl_language(settings.target_language)
    if not source_language or not target_language:
        return None

    payload_pairs = [
        ("auth_key", api_key),
        ("source_lang", source_language),
        ("target_lang", target_language),
    ]
    payload_pairs.extend(("text", text) for text in texts)
    payload = parse.urlencode(payload_pairs).encode("utf-8")
    req = request.Request(
        config.deepl_api_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=config.deepl_timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, error.URLError, error.HTTPError, json.JSONDecodeError):
        return None

    translations = data.get("translations", [])
    if len(translations) != len(texts):
        return None
    return [str(item.get("text", source)).strip() or source for item, source in zip(translations, texts, strict=False)]


def _deepl_language(language: str) -> str | None:
    return {
        "en": "EN",
        "ja": "JA",
        "ko": "KO",
    }.get(language)


def _parse_numbered_translations(response: str, *, expected_count: int) -> list[str]:
    translation_map = _parse_numbered_translation_map(response)
    if translation_map:
        return [translation_map[index] for index in sorted(translation_map)[:expected_count]]

    translations: list[str] = []
    for raw_line in response.splitlines():
        line = raw_line.strip()
        if line:
            translations.append(line)
    return translations[:expected_count]


def _parse_numbered_translation_map(response: str) -> dict[int, str]:
    translations: dict[int, str] = {}
    pending_index: int | None = None
    pending_lines: list[str] = []

    def flush_pending() -> None:
        nonlocal pending_index, pending_lines
        if pending_index is None:
            return
        text = " ".join(line.strip() for line in pending_lines if line.strip()).strip()
        if text:
            translations[pending_index] = text
        pending_index = None
        pending_lines = []

    for raw_line in response.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^\s*(\d+)\s*(?:[\|).\]:：-]|\s+-\s+)\s*(.+?)\s*$", line)
        if match:
            flush_pending()
            pending_index = int(match.group(1))
            pending_lines = [match.group(2)]
            continue
        if pending_index is not None:
            pending_lines.append(line)

    flush_pending()
    return translations


def _normalize_translation_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _render_translated_image(
    image_path: Path,
    image,
    translations: list[tuple[OcrTextBox, str]],
    settings: ImageTranslationSettings,
    *,
    suffix: str = "_translated",
) -> Path:
    try:
        from PIL import ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow가 설치되어 있지 않습니다. pip install -e . 명령으로 의존성을 다시 설치해 주세요.") from exc

    output = image.copy()
    draw = ImageDraw.Draw(output)
    for box, translated_text in translations:
        padding = 4
        left = max(0, box.left - padding)
        top = max(0, box.top - padding)
        right = min(output.width, box.left + box.width + padding)
        bottom = min(output.height, box.top + box.height + padding)
        draw.rectangle((left, top, right, bottom), fill="white")
        font = _load_translation_font(max(12, min(28, int((bottom - top) * 0.7))))
        wrapped = _wrap_text_for_width(translated_text, max(1, right - left - padding * 2), font)
        draw.multiline_text((left + padding, top + padding), wrapped, fill="black", font=font, spacing=2)

    output_path = _output_path(image_path, settings, suffix=suffix)
    output.save(output_path)
    return output_path


def _render_ocr_review_image(
    image_path: Path,
    image,
    boxes: list[OcrTextBox],
    settings: ImageTranslationSettings,
) -> Path:
    try:
        from PIL import ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow가 설치되어 있지 않습니다. pip install -e . 명령으로 의존성을 다시 설치해 주세요.") from exc

    output = image.copy()
    draw = ImageDraw.Draw(output)
    for box in boxes:
        padding = 4
        left = max(0, box.left - padding)
        top = max(0, box.top - padding)
        right = min(output.width, box.left + box.width + padding)
        bottom = min(output.height, box.top + box.height + padding)
        for offset in range(3):
            draw.rectangle((left - offset, top - offset, right + offset, bottom + offset), outline="white")

    output_path = _output_path(image_path, settings, suffix="_ocr_review")
    output.save(output_path)
    return output_path


def _output_path(image_path: Path, settings: ImageTranslationSettings, *, suffix: str) -> Path:
    output_dir = settings.output_dir or image_path.parent / "translated"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{image_path.stem}{suffix}.png"


def _load_translation_font(size: int):
    from PIL import ImageFont

    font_paths = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for font_path in font_paths:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def _wrap_text_for_width(text: str, width: int, font) -> str:
    average_char_width = max(1, int(font.getlength("가" if any("\uac00" <= char <= "\ud7a3" for char in text) else "M")))
    max_chars = max(4, width // average_char_width)
    return "\n".join(textwrap.wrap(text, width=max_chars)) or text


def _describe_preprocessing(settings: ImageTranslationSettings) -> str:
    parts = [f"{settings.upscale_factor}x 업스케일"]
    if settings.enhance_contrast:
        parts.append("대비 강화")
    if settings.grayscale:
        parts.append("흑백 처리")
    parts.append(f"최소 신뢰도 {settings.min_confidence:.2f}")
    return ", ".join(parts)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def _is_cancelled(should_cancel: Callable[[], bool] | None) -> bool:
    return bool(should_cancel and should_cancel())
