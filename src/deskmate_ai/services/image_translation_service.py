from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
    cache_group_name: str
    output_dir: Path | None = None


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


def run_image_translation(
    image_paths: list[Path],
    settings: ImageTranslationSettings,
    *,
    config: AppConfig = DEFAULT_CONFIG,
) -> Iterable[ImageTranslationProgress]:
    total = estimate_total_steps(len(image_paths), settings)
    current = 0
    if total == 0:
        yield ImageTranslationProgress(0, 0, "대기", "처리할 이미지가 없습니다.")
        return

    for image_path in image_paths:
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

        current += 1
        translations = _translate_boxes(text_boxes, settings, config=config)
        yield ImageTranslationProgress(
            current,
            total,
            "번역",
            f"{image_path.name}: {len(translations)}개 텍스트 번역",
        )

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
            f"{image_path.name}: {settings.source_language}->{settings.target_language}, {settings.cache_group_name}",
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

    boxes: list[OcrTextBox] = []
    min_confidence = settings.min_confidence * 100
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
        boxes.append(
            OcrTextBox(
                text=text,
                left=int(data["left"][index]),
                top=int(data["top"][index]),
                width=int(data["width"][index]),
                height=int(data["height"][index]),
                confidence=confidence / 100,
            )
        )
    return boxes


def _translate_boxes(
    boxes: list[OcrTextBox],
    settings: ImageTranslationSettings,
    *,
    config: AppConfig,
) -> list[tuple[OcrTextBox, str]]:
    translations: list[tuple[OcrTextBox, str]] = []
    cache: dict[str, str] = {}
    for box in boxes:
        if box.text not in cache:
            cache[box.text] = _translate_text(box.text, settings, config=config)
        translations.append((box, cache[box.text]))
    return translations


def _translate_text(text: str, settings: ImageTranslationSettings, *, config: AppConfig) -> str:
    if settings.source_language == settings.target_language:
        return text
    prompt = (
        "Translate the following text. "
        f"Source language: {settings.source_language}. "
        f"Target language: {settings.target_language}. "
        "Return only the translated text, with no explanation.\n\n"
        f"{text}"
    )
    translated = ask_local_model(prompt, config=config)
    return translated or text


def _render_translated_image(
    image_path: Path,
    image,
    translations: list[tuple[OcrTextBox, str]],
    settings: ImageTranslationSettings,
) -> Path:
    try:
        from PIL import ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow가 설치되어 있지 않습니다. pip install -e . 명령으로 의존성을 다시 설치해 주세요.") from exc

    output = image.copy()
    draw = ImageDraw.Draw(output)
    font = ImageFont.load_default()
    for box, translated_text in translations:
        padding = 3
        left = max(0, box.left - padding)
        top = max(0, box.top - padding)
        right = min(output.width, box.left + box.width + padding)
        bottom = min(output.height, box.top + box.height + padding)
        draw.rectangle((left, top, right, bottom), fill="white")
        wrapped = _wrap_text_for_width(translated_text, max(1, right - left), font)
        draw.multiline_text((left + padding, top + padding), wrapped, fill="black", font=font, spacing=2)

    output_dir = settings.output_dir or image_path.parent / "translated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{image_path.stem}_translated.png"
    output.save(output_path)
    return output_path


def _wrap_text_for_width(text: str, width: int, font) -> str:
    average_char_width = max(1, int(font.getlength("M")))
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
