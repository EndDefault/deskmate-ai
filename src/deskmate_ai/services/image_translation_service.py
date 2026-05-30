from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


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


@dataclass(frozen=True)
class ImageTranslationProgress:
    current: int
    total: int
    stage: str
    message: str

    @property
    def ratio(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.current / self.total))


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
        preprocessing = _describe_preprocessing(settings)
        yield ImageTranslationProgress(current, total, "전처리", f"{image_path.name}: {preprocessing}")

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
