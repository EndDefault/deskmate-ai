from __future__ import annotations

from pathlib import Path
from threading import Thread
from tkinter import filedialog

import customtkinter as ctk

from deskmate_ai.services.image_translation_service import (
    ImageTranslationSettings,
    collect_image_paths,
    run_image_translation_preview,
)
from deskmate_ai.services.storage_service import list_keyword_cache_categories
from deskmate_ai.ui.constants import LANGUAGE_PAIRS
from deskmate_ai.ui.windows.base_window import BaseWindow


class ImageTranslationWindow(BaseWindow):
    def __init__(self, parent) -> None:
        super().__init__(parent, title="Image translation", geometry="720x680")
        self.selected_sources: list[Path] = []
        self.selected_images: list[Path] = []
        self.is_running = False
        self._build()

    def _build(self) -> None:
        self.header("Image translation")

        source_frame = ctk.CTkFrame(self.container)
        source_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(source_frame, text="Select images", command=self.select_images).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(source_frame, text="Select folder", command=self.select_folder).pack(side="left", padx=(0, 8), pady=8)
        self.source_label = ctk.CTkLabel(source_frame, text="Selected images: 0", anchor="w")
        self.source_label.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)

        settings = ctk.CTkFrame(self.container)
        settings.pack(fill="x", pady=(0, 12))
        settings.grid_columnconfigure(1, weight=1)
        settings.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(settings, text="Language", anchor="w").grid(row=0, column=0, padx=8, pady=(8, 4), sticky="w")
        self.language_menu = ctk.CTkOptionMenu(settings, values=list(LANGUAGE_PAIRS.keys()))
        self.language_menu.set(next(iter(LANGUAGE_PAIRS)))
        self.language_menu.grid(row=0, column=1, columnspan=3, padx=8, pady=(8, 4), sticky="ew")

        ctk.CTkLabel(settings, text="OCR passes").grid(row=1, column=0, padx=8, pady=4, sticky="w")
        self.ocr_passes = ctk.CTkOptionMenu(settings, values=["1", "2", "3", "4", "5"])
        self.ocr_passes.set("3")
        self.ocr_passes.grid(row=1, column=1, padx=8, pady=4, sticky="ew")

        ctk.CTkLabel(settings, text="Upscale").grid(row=1, column=2, padx=8, pady=4, sticky="w")
        self.upscale_factor = ctk.CTkOptionMenu(settings, values=["1", "2", "3"])
        self.upscale_factor.set("2")
        self.upscale_factor.grid(row=1, column=3, padx=8, pady=4, sticky="ew")

        self.contrast_enabled = ctk.BooleanVar(value=True)
        self.grayscale_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings, text="Enhance contrast", variable=self.contrast_enabled).grid(
            row=2, column=0, columnspan=2, padx=8, pady=4, sticky="w"
        )
        ctk.CTkCheckBox(settings, text="Grayscale", variable=self.grayscale_enabled).grid(
            row=2, column=2, columnspan=2, padx=8, pady=4, sticky="w"
        )

        ctk.CTkLabel(settings, text="Min confidence").grid(row=3, column=0, padx=8, pady=(4, 8), sticky="w")
        self.min_confidence = ctk.CTkSlider(settings, from_=0.1, to=0.95, number_of_steps=17)
        self.min_confidence.set(0.55)
        self.min_confidence.grid(row=3, column=1, columnspan=3, padx=8, pady=(4, 8), sticky="ew")

        cache_frame = ctk.CTkFrame(self.container)
        cache_frame.pack(fill="x", pady=(0, 12))
        cache_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cache_frame, text="Cache category", anchor="w").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        self.cache_group_menu = ctk.CTkOptionMenu(cache_frame, values=self._cache_category_names())
        self.cache_group_menu.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

        self.progress = ctk.CTkProgressBar(self.container)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.status_label = ctk.CTkLabel(self.container, text="Ready", anchor="w")
        self.status_label.pack(fill="x", pady=(0, 8))
        self.log = ctk.CTkTextbox(self.container, wrap="word", height=220)
        self.log.pack(fill="both", expand=True, pady=(0, 12))
        self.start_button = ctk.CTkButton(self.container, text="Start", command=self.start_translation)
        self.start_button.pack(anchor="e")

    def select_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")],
        )
        if paths:
            self.selected_sources = [Path(path) for path in paths]
            self._refresh_selected_images()

    def select_folder(self) -> None:
        path = filedialog.askdirectory(title="Select image folder")
        if path:
            self.selected_sources = [Path(path)]
            self._refresh_selected_images()

    def start_translation(self) -> None:
        if self.is_running:
            return
        self._refresh_selected_images()
        if not self.selected_images:
            self.status_label.configure(text="Select images to process.")
            return

        self.is_running = True
        self.start_button.configure(state="disabled", text="Running")
        self.log.delete("1.0", "end")
        Thread(target=self._run_translation, args=(self._settings(),), daemon=True).start()

    def _run_translation(self, settings: ImageTranslationSettings) -> None:
        for progress in run_image_translation_preview(self.selected_images, settings):
            self.after(0, self._update_progress, progress.ratio, f"{progress.stage}: {progress.message}")
        self.after(0, self._finish_translation)

    def _update_progress(self, ratio: float, message: str) -> None:
        self.progress.set(ratio)
        self.status_label.configure(text=message)
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def _finish_translation(self) -> None:
        self.is_running = False
        self.start_button.configure(state="normal", text="Start")
        self.status_label.configure(text="Preview complete")

    def _refresh_selected_images(self) -> None:
        self.selected_images = collect_image_paths(self.selected_sources)
        self.source_label.configure(text=f"Selected images: {len(self.selected_images)}")

    def _settings(self) -> ImageTranslationSettings:
        source_language, target_language = LANGUAGE_PAIRS[self.language_menu.get()]
        return ImageTranslationSettings(
            source_language=source_language,
            target_language=target_language,
            ocr_passes=int(self.ocr_passes.get()),
            upscale_factor=int(self.upscale_factor.get()),
            enhance_contrast=self.contrast_enabled.get(),
            grayscale=self.grayscale_enabled.get(),
            min_confidence=float(self.min_confidence.get()),
            cache_group_name=self.cache_group_menu.get(),
        )

    def _cache_category_names(self) -> list[str]:
        names = [category.name for category in list_keyword_cache_categories()]
        return names or ["Default cache"]
