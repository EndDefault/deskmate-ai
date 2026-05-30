from __future__ import annotations

from pathlib import Path
from threading import Thread
from tkinter import filedialog

import customtkinter as ctk

from deskmate_ai.services.image_translation_service import (
    ImageTranslationSettings,
    collect_image_paths,
    run_image_translation,
)
from deskmate_ai.services.storage_service import list_translation_cache_groups
from deskmate_ai.ui.constants import SOURCE_LANGUAGES, TARGET_LANGUAGES
from deskmate_ai.ui.windows.base_window import BaseWindow
from deskmate_ai.ui.windows.translation_cache_window import TranslationCacheWindow


NO_OPTIONAL_CACHE = "사용 안 함"
NO_REQUIRED_CACHE = "사용 가능한 캐시 없음"


class ImageTranslationWindow(BaseWindow):
    def __init__(self, parent) -> None:
        super().__init__(parent, title="이미지 번역", geometry="760x700")
        self.selected_sources: list[Path] = []
        self.selected_images: list[Path] = []
        self.is_running = False
        self._build()

    def _build(self) -> None:
        self.header("이미지 번역 작업")

        source_frame = ctk.CTkFrame(self.container)
        source_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(source_frame, text="이미지 선택", command=self.select_images).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(source_frame, text="폴더 선택", command=self.select_folder).pack(side="left", padx=(0, 8), pady=8)
        self.source_label = ctk.CTkLabel(source_frame, text="선택한 이미지: 0개", anchor="w")
        self.source_label.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)

        settings = ctk.CTkFrame(self.container)
        settings.pack(fill="x", pady=(0, 12))
        settings.grid_columnconfigure(1, weight=1)
        settings.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(settings, text="원문 언어", anchor="w").grid(row=0, column=0, padx=8, pady=(8, 4), sticky="w")
        self.source_language_menu = ctk.CTkOptionMenu(
            settings,
            values=list(SOURCE_LANGUAGES.keys()),
            command=lambda _: self._refresh_cache_groups(),
        )
        self.source_language_menu.set("영어")
        self.source_language_menu.grid(row=0, column=1, padx=8, pady=(8, 4), sticky="ew")

        ctk.CTkLabel(settings, text="번역 언어", anchor="w").grid(row=0, column=2, padx=8, pady=(8, 4), sticky="w")
        self.target_language_menu = ctk.CTkOptionMenu(settings, values=list(TARGET_LANGUAGES.keys()))
        self.target_language_menu.set("한국어")
        self.target_language_menu.grid(row=0, column=3, padx=8, pady=(8, 4), sticky="ew")

        ctk.CTkLabel(settings, text="OCR 반복").grid(row=1, column=0, padx=8, pady=4, sticky="w")
        self.ocr_passes = ctk.CTkOptionMenu(settings, values=["1", "2", "3", "4", "5"])
        self.ocr_passes.set("3")
        self.ocr_passes.grid(row=1, column=1, padx=8, pady=4, sticky="ew")

        ctk.CTkLabel(settings, text="업스케일").grid(row=1, column=2, padx=8, pady=4, sticky="w")
        self.upscale_factor = ctk.CTkOptionMenu(settings, values=["1", "2", "3"])
        self.upscale_factor.set("2")
        self.upscale_factor.grid(row=1, column=3, padx=8, pady=4, sticky="ew")

        self.contrast_enabled = ctk.BooleanVar(value=True)
        self.grayscale_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings, text="대비 강화", variable=self.contrast_enabled).grid(
            row=2, column=0, columnspan=2, padx=8, pady=4, sticky="w"
        )
        ctk.CTkCheckBox(settings, text="흑백 처리", variable=self.grayscale_enabled).grid(
            row=2, column=2, columnspan=2, padx=8, pady=4, sticky="w"
        )

        ctk.CTkLabel(settings, text="최소 신뢰도").grid(row=3, column=0, padx=8, pady=(4, 8), sticky="w")
        self.min_confidence = ctk.CTkSlider(settings, from_=0.1, to=0.95, number_of_steps=17)
        self.min_confidence.set(0.55)
        self.min_confidence.grid(row=3, column=1, columnspan=3, padx=8, pady=(4, 8), sticky="ew")

        cache_frame = ctk.CTkFrame(self.container)
        cache_frame.pack(fill="x", pady=(0, 12))
        cache_frame.grid_columnconfigure(1, weight=1)
        cache_frame.grid_columnconfigure(3, weight=1)
        cache_frame.grid_columnconfigure(5, weight=1)
        ctk.CTkLabel(cache_frame, text="번역 캐시 1", anchor="w").grid(row=0, column=0, padx=8, pady=(8, 4), sticky="w")
        self.primary_cache_menu = ctk.CTkOptionMenu(
            cache_frame,
            values=[NO_REQUIRED_CACHE],
            command=lambda _: self._sync_cache_dropdowns(),
        )
        self.primary_cache_menu.grid(row=0, column=1, padx=8, pady=(8, 4), sticky="ew")

        ctk.CTkLabel(cache_frame, text="번역 캐시 2", anchor="w").grid(row=0, column=2, padx=8, pady=(8, 4), sticky="w")
        self.secondary_cache_menu = ctk.CTkOptionMenu(
            cache_frame,
            values=[NO_OPTIONAL_CACHE],
            command=lambda _: self._sync_cache_dropdowns(),
        )
        self.secondary_cache_menu.grid(row=0, column=3, padx=8, pady=(8, 4), sticky="ew")

        ctk.CTkLabel(cache_frame, text="번역 캐시 3", anchor="w").grid(row=1, column=0, padx=8, pady=(4, 8), sticky="w")
        self.tertiary_cache_menu = ctk.CTkOptionMenu(
            cache_frame,
            values=[NO_OPTIONAL_CACHE],
            command=lambda _: self._sync_cache_dropdowns(),
        )
        self.tertiary_cache_menu.grid(row=1, column=1, padx=8, pady=(4, 8), sticky="ew")

        ctk.CTkButton(cache_frame, text="번역용 캐시 보기", command=self.show_translation_cache).grid(
            row=1, column=5, padx=8, pady=(4, 8), sticky="e"
        )
        self._refresh_cache_groups()

        self.progress = ctk.CTkProgressBar(self.container)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.status_label = ctk.CTkLabel(self.container, text="대기 중", anchor="w")
        self.status_label.pack(fill="x", pady=(0, 8))
        self.log = ctk.CTkTextbox(self.container, wrap="word", height=220)
        self.log.pack(fill="both", expand=True, pady=(0, 12))
        self.start_button = ctk.CTkButton(self.container, text="시작", command=self.start_translation)
        self.start_button.pack(anchor="e")

    def select_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="번역할 이미지 선택",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")],
        )
        if paths:
            self.selected_sources = [Path(path) for path in paths]
            self._refresh_selected_images()

    def select_folder(self) -> None:
        path = filedialog.askdirectory(title="이미지가 들어 있는 폴더 선택")
        if path:
            self.selected_sources = [Path(path)]
            self._refresh_selected_images()

    def start_translation(self) -> None:
        if self.is_running:
            return
        self._refresh_selected_images()
        if not self.selected_images:
            self.status_label.configure(text="처리할 이미지를 선택해 주세요.")
            return
        if not self._selected_cache_group_names():
            self.status_label.configure(text="원문 언어에 맞는 번역 캐시를 먼저 만들어 주세요.")
            return

        self.is_running = True
        self.start_button.configure(state="disabled", text="실행 중")
        self.log.delete("1.0", "end")
        Thread(target=self._run_translation, args=(self._settings(),), daemon=True).start()

    def _run_translation(self, settings: ImageTranslationSettings) -> None:
        for progress in run_image_translation(self.selected_images, settings):
            self.after(0, self._update_progress, progress.ratio, f"{progress.stage}: {progress.message}")
        self.after(0, self._finish_translation)

    def _update_progress(self, ratio: float, message: str) -> None:
        self.progress.set(ratio)
        self.status_label.configure(text=message)
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def _finish_translation(self) -> None:
        self.is_running = False
        self.start_button.configure(state="normal", text="시작")
        self.status_label.configure(text="작업 완료")

    def _refresh_selected_images(self) -> None:
        self.selected_images = collect_image_paths(self.selected_sources)
        self.source_label.configure(text=f"선택한 이미지: {len(self.selected_images)}개")

    def show_translation_cache(self) -> None:
        window = TranslationCacheWindow(self, on_change=self._refresh_cache_groups)
        window.focus()

    def _settings(self) -> ImageTranslationSettings:
        return ImageTranslationSettings(
            source_language=SOURCE_LANGUAGES[self.source_language_menu.get()],
            target_language=TARGET_LANGUAGES[self.target_language_menu.get()],
            ocr_passes=int(self.ocr_passes.get()),
            upscale_factor=int(self.upscale_factor.get()),
            enhance_contrast=self.contrast_enabled.get(),
            grayscale=self.grayscale_enabled.get(),
            min_confidence=float(self.min_confidence.get()),
            cache_group_names=self._selected_cache_group_names(),
        )

    def _cache_category_names(self) -> list[str]:
        source_language = SOURCE_LANGUAGES[self.source_language_menu.get()]
        return [group.name for group in list_translation_cache_groups() if group.source_language == source_language]

    def _refresh_cache_groups(self) -> None:
        previous = self._selected_cache_group_names()
        names = self._cache_category_names()

        self.primary_cache_menu.set(previous[0] if previous and previous[0] in names else (names[0] if names else NO_REQUIRED_CACHE))
        self.secondary_cache_menu.set(previous[1] if len(previous) > 1 and previous[1] in names else NO_OPTIONAL_CACHE)
        self.tertiary_cache_menu.set(previous[2] if len(previous) > 2 and previous[2] in names else NO_OPTIONAL_CACHE)
        self._sync_cache_dropdowns()

    def _sync_cache_dropdowns(self) -> None:
        names = self._cache_category_names()
        primary = self.primary_cache_menu.get()
        secondary = self.secondary_cache_menu.get()
        tertiary = self.tertiary_cache_menu.get()

        if primary not in names:
            primary = names[0] if names else NO_REQUIRED_CACHE
        if secondary not in names:
            secondary = NO_OPTIONAL_CACHE
        if tertiary not in names:
            tertiary = NO_OPTIONAL_CACHE

        if secondary == primary:
            secondary = NO_OPTIONAL_CACHE
        if tertiary in {primary, secondary}:
            tertiary = NO_OPTIONAL_CACHE

        self.primary_cache_menu.set(primary)
        self.secondary_cache_menu.set(secondary)
        self.tertiary_cache_menu.set(tertiary)

        self.primary_cache_menu.configure(values=self._cache_options(names, primary, [secondary, tertiary], required=True))
        self.secondary_cache_menu.configure(values=self._cache_options(names, secondary, [primary, tertiary]))
        self.tertiary_cache_menu.configure(values=self._cache_options(names, tertiary, [primary, secondary]))

    def _cache_options(
        self,
        names: list[str],
        current: str,
        selected_elsewhere: list[str],
        *,
        required: bool = False,
    ) -> list[str]:
        blocked = {name for name in selected_elsewhere if name not in {NO_OPTIONAL_CACHE, NO_REQUIRED_CACHE}}
        values = [name for name in names if name not in blocked or name == current]
        if required:
            return values or [NO_REQUIRED_CACHE]
        return [NO_OPTIONAL_CACHE, *values]

    def _selected_cache_group_names(self) -> list[str]:
        selected = [
            self.primary_cache_menu.get(),
            self.secondary_cache_menu.get(),
            self.tertiary_cache_menu.get(),
        ]
        result: list[str] = []
        for name in selected:
            if name in {NO_OPTIONAL_CACHE, NO_REQUIRED_CACHE} or name in result:
                continue
            result.append(name)
        return result
