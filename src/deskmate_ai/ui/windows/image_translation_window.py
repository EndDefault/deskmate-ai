from __future__ import annotations

import tkinter as tk
from pathlib import Path
from threading import Event, Thread
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

from deskmate_ai.services.image_translation_service import (
    ImageTranslationSettings,
    OcrReviewResult,
    TranslationReviewResult,
    add_manual_ocr_box,
    approve_translation_review,
    collect_image_paths,
    delete_ocr_box,
    format_ocr_review_text,
    format_translation_review_text,
    prepare_ocr_review,
    prepare_translation_review,
)
from deskmate_ai.services.storage_service import list_translation_cache_groups
from deskmate_ai.ui.constants import SOURCE_LANGUAGES, TARGET_LANGUAGES
from deskmate_ai.ui.windows.base_window import BaseWindow
from deskmate_ai.ui.windows.translation_cache_window import TranslationCacheWindow


NO_OPTIONAL_CACHE = "사용 안 함"
NO_REQUIRED_CACHE = "사용 가능한 캐시 없음"


class ImageTranslationReviewWindow(BaseWindow):
    def __init__(
        self,
        parent,
        *,
        title: str,
        image_path: Path,
        body: str,
        approve_command,
        reject_command,
        add_box_command=None,
        delete_box_command=None,
    ) -> None:
        super().__init__(parent, title=title, geometry="980x720")
        self.approve_command = approve_command
        self.reject_command = reject_command
        self.add_box_command = add_box_command
        self.delete_box_command = delete_box_command
        self.preview_image = None
        self.preview_photo = None
        self.preview_scale = 1.0
        self.selected_box: tuple[int, int, int, int] | None = None
        self.drag_start: tuple[int, int] | None = None
        self.drag_rectangle = None
        self.header(title)

        review_frame = ctk.CTkFrame(self.container)
        review_frame.pack(fill="both", expand=True, pady=(0, 12))
        review_frame.grid_columnconfigure(0, weight=3)
        review_frame.grid_columnconfigure(1, weight=2)
        review_frame.grid_rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(review_frame, bg="#111111", highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self._show_preview_image(image_path)

        side_panel = ctk.CTkFrame(review_frame, fg_color="transparent")
        side_panel.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="nsew")
        side_panel.grid_rowconfigure(0, weight=1)
        side_panel.grid_columnconfigure(0, weight=1)

        self.body = body
        if delete_box_command is None:
            self.text_box = ctk.CTkTextbox(side_panel, wrap="word")
            self.text_box.grid(row=0, column=0, sticky="nsew")
            self._set_body(body)
            self.item_list = None
        else:
            self.text_box = None
            self.item_list = ctk.CTkScrollableFrame(side_panel)
            self.item_list.grid(row=0, column=0, sticky="nsew")
            self._set_body(body)

        if add_box_command is not None:
            manual_frame = ctk.CTkFrame(side_panel)
            manual_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            manual_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(manual_frame, text="누락 영역을 이미지에서 드래그한 뒤 원문을 입력하세요.", anchor="w").grid(
                row=0,
                column=0,
                padx=8,
                pady=(8, 4),
                sticky="ew",
            )
            self.manual_text = ctk.CTkEntry(manual_frame, placeholder_text="누락된 영어 원문")
            self.manual_text.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
            ctk.CTkButton(manual_frame, text="영역 추가", command=self._add_manual_box).grid(
                row=2,
                column=0,
                padx=8,
                pady=(0, 8),
                sticky="ew",
            )
            self.preview_canvas.bind("<ButtonPress-1>", self._start_drag)
            self.preview_canvas.bind("<B1-Motion>", self._drag)
            self.preview_canvas.bind("<ButtonRelease-1>", self._finish_drag)

        actions = ctk.CTkFrame(self.container, fg_color="transparent")
        actions.pack(fill="x")
        ctk.CTkButton(actions, text="불통과", fg_color="#b91c1c", command=self._reject).pack(side="left")
        ctk.CTkButton(actions, text="통과", command=self._approve).pack(side="right")

    def _show_preview_image(self, image_path: Path) -> None:
        image = Image.open(image_path)
        max_width = 560
        max_height = 560
        self.preview_scale = min(max_width / image.width, max_height / image.height, 1)
        size = (max(1, int(image.width * self.preview_scale)), max(1, int(image.height * self.preview_scale)))
        self.preview_image = image.resize(size)
        self.preview_photo = ImageTk.PhotoImage(self.preview_image)
        self.preview_canvas.configure(width=size[0], height=size[1], scrollregion=(0, 0, size[0], size[1]))
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")

    def _set_body(self, body: str) -> None:
        self.body = body
        if self.item_list is not None:
            self._render_deletable_items(body)
            return
        if self.text_box is None:
            return
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("end", body)
        self.text_box.configure(state="disabled")

    def _render_deletable_items(self, body: str) -> None:
        if self.item_list is None:
            return
        for child in self.item_list.winfo_children():
            child.destroy()
        lines = body.splitlines() or ["OCR로 감지한 텍스트가 없습니다."]
        for index, line in enumerate(lines):
            row = ctk.CTkFrame(self.item_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            delete_button = ctk.CTkButton(
                row,
                text="X",
                width=32,
                fg_color="#b91c1c",
                command=lambda row_index=index: self._delete_box(row_index),
            )
            delete_button.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(row, text=line, anchor="w", justify="left", wraplength=330).pack(side="left", fill="x", expand=True)

    def _start_drag(self, event) -> None:
        self.drag_start = (event.x, event.y)
        if self.drag_rectangle is not None:
            self.preview_canvas.delete(self.drag_rectangle)
        self.drag_rectangle = self.preview_canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#38bdf8", width=2)

    def _drag(self, event) -> None:
        if self.drag_start is None or self.drag_rectangle is None:
            return
        start_x, start_y = self.drag_start
        self.preview_canvas.coords(self.drag_rectangle, start_x, start_y, event.x, event.y)

    def _finish_drag(self, event) -> None:
        if self.drag_start is None:
            return
        start_x, start_y = self.drag_start
        left = max(0, min(start_x, event.x))
        top = max(0, min(start_y, event.y))
        right = max(start_x, event.x)
        bottom = max(start_y, event.y)
        if right - left < 4 or bottom - top < 4:
            self.selected_box = None
            return
        self.selected_box = (
            int(left / self.preview_scale),
            int(top / self.preview_scale),
            int((right - left) / self.preview_scale),
            int((bottom - top) / self.preview_scale),
        )

    def _add_manual_box(self) -> None:
        if self.add_box_command is None or self.selected_box is None:
            return
        text = self.manual_text.get().strip()
        if not text:
            return
        image_path, body = self.add_box_command(text, self.selected_box)
        self.manual_text.delete(0, "end")
        self.selected_box = None
        self._show_preview_image(image_path)
        self._set_body(body)

    def _delete_box(self, index: int) -> None:
        if self.delete_box_command is None:
            return
        image_path, body = self.delete_box_command(index)
        self._show_preview_image(image_path)
        self._set_body(body)

    def _approve(self) -> None:
        self.destroy()
        self.approve_command()

    def _reject(self) -> None:
        self.destroy()
        self.reject_command()


class ImageTranslationWindow(BaseWindow):
    def __init__(self, parent) -> None:
        super().__init__(parent, title="이미지 번역", geometry="820x720")
        self.selected_sources: list[Path] = []
        self.selected_images: list[Path] = []
        self.cancel_event = Event()
        self.is_running = False
        self.current_index = 0
        self.current_stage = "idle"
        self.current_settings: ImageTranslationSettings | None = None
        self.current_ocr_review: OcrReviewResult | None = None
        self.current_translation_review: TranslationReviewResult | None = None
        self.review_window: ImageTranslationReviewWindow | None = None
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

        ctk.CTkLabel(settings, text="번역 엔진", anchor="w").grid(row=4, column=0, padx=8, pady=(4, 8), sticky="w")
        self.translation_provider_menu = ctk.CTkOptionMenu(settings, values=["로컬 AI", "DeepL 무료 API"])
        self.translation_provider_menu.set("로컬 AI")
        self.translation_provider_menu.grid(row=4, column=1, columnspan=3, padx=8, pady=(4, 8), sticky="ew")

        ctk.CTkLabel(settings, text="OCR 반복").grid(row=1, column=0, padx=8, pady=4, sticky="w")
        self.ocr_passes = ctk.CTkOptionMenu(settings, values=["1", "2", "3", "4", "5"])
        self.ocr_passes.set("1")
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

        actions = ctk.CTkFrame(self.container, fg_color="transparent")
        actions.pack(side="bottom", fill="x")
        self.cancel_button = ctk.CTkButton(actions, text="강제 종료", state="disabled", command=self.cancel_translation)
        self.cancel_button.pack(side="right")
        self.start_button = ctk.CTkButton(actions, text="시작", command=self.start_translation)
        self.start_button.pack(side="right", padx=(0, 8))

        self.log = ctk.CTkTextbox(self.container, wrap="word", height=220)
        self.log.pack(fill="both", expand=True, pady=(0, 12))

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

        self.is_running = True
        self.cancel_event.clear()
        self.current_index = 0
        self.current_settings = self._settings()
        self.current_ocr_review = None
        self.current_translation_review = None
        self.current_stage = "ocr"
        self.start_button.configure(state="disabled", text="실행 중")
        self.cancel_button.configure(state="normal", text="강제 종료")
        self.log.delete("1.0", "end")
        self._start_ocr_stage()

    def _start_ocr_stage(self) -> None:
        if self.cancel_event.is_set() or self.current_settings is None:
            self._finish_translation("작업 중단")
            return
        if self.current_index >= len(self.selected_images):
            self._finish_translation("모든 이미지 작업 완료")
            return
        image_path = self.selected_images[self.current_index]
        self.current_stage = "ocr_loading"
        self._update_progress(self.current_index / max(1, len(self.selected_images)), f"OCR 준비: {image_path.name}")
        Thread(target=self._run_ocr_stage, args=(image_path, self.current_settings), daemon=True).start()

    def _run_ocr_stage(self, image_path: Path, settings: ImageTranslationSettings) -> None:
        try:
            review = prepare_ocr_review(image_path, settings)
        except RuntimeError as exc:
            self.after(0, self._stage_failed, f"OCR 오류: {exc}")
            return
        self.after(0, self._show_ocr_review, review)

    def _show_ocr_review(self, review: OcrReviewResult) -> None:
        self.current_stage = "ocr_review"
        self.current_ocr_review = review
        self.current_translation_review = None
        self._open_review_window(
            title="OCR 검수",
            image_path=review.preview_path,
            body=format_ocr_review_text(review.boxes),
            add_box_command=self.add_manual_ocr_box_to_review,
            delete_box_command=self.delete_ocr_box_from_review,
        )
        self._update_progress(
            (self.current_index + 0.35) / max(1, len(self.selected_images)),
            f"OCR 검수 대기: {review.image_path.name} / {len(review.boxes)}개 감지",
        )

    def _start_translation_stage(self) -> None:
        if self.cancel_event.is_set() or self.current_settings is None or self.current_ocr_review is None:
            self._finish_translation("작업 중단")
            return
        self.current_stage = "translation_loading"
        self._update_progress(
            (self.current_index + 0.55) / max(1, len(self.selected_images)),
            f"번역 준비: {self.current_ocr_review.image_path.name}",
        )
        Thread(
            target=self._run_translation_stage,
            args=(self.current_ocr_review, self.current_settings),
            daemon=True,
        ).start()

    def _run_translation_stage(self, review: OcrReviewResult, settings: ImageTranslationSettings) -> None:
        try:
            translated = prepare_translation_review(review, settings)
        except RuntimeError as exc:
            self.after(0, self._stage_failed, f"번역 오류: {exc}")
            return
        self.after(0, self._show_translation_review, translated)

    def _show_translation_review(self, review: TranslationReviewResult) -> None:
        self.current_stage = "translation_review"
        self.current_translation_review = review
        self._open_review_window(
            title="번역 검수",
            image_path=review.preview_path,
            body=format_translation_review_text(review.translations),
        )
        self._update_progress(
            (self.current_index + 0.85) / max(1, len(self.selected_images)),
            f"번역 검수 대기: {review.image_path.name}",
        )

    def approve_current_stage(self) -> None:
        if self.current_stage == "ocr_review":
            self._start_translation_stage()
            return
        if self.current_stage == "translation_review" and self.current_translation_review is not None:
            output_path = approve_translation_review(self.current_translation_review)
            self._update_progress(
                (self.current_index + 1) / max(1, len(self.selected_images)),
                f"결과 저장: {output_path}",
            )
            self.current_index += 1
            self._start_ocr_stage()

    def reject_current_stage(self) -> None:
        if self.current_stage == "ocr_review":
            self._finish_translation("OCR 불통과: 설정을 조정하거나 누락 영역을 확인해 주세요.")
            return
        if self.current_stage == "translation_review":
            self._finish_translation("번역 불통과: 번역 결과를 확인해 주세요.")

    def _stage_failed(self, message: str) -> None:
        self._update_progress(0, message)
        self._finish_translation(message)

    def cancel_translation(self) -> None:
        if not self.is_running:
            return
        self.cancel_event.set()
        self._close_review_window()
        self.cancel_button.configure(state="disabled", text="종료 중")
        self.status_label.configure(text="현재 단계가 끝나면 작업을 중단합니다.")

    def _update_progress(self, ratio: float, message: str) -> None:
        self.progress.set(ratio)
        self.status_label.configure(text=message)
        self.log.insert("end", message + "\n")
        self.log.see("end")

    def _finish_translation(self, message: str = "작업 완료") -> None:
        self.is_running = False
        self.current_stage = "idle"
        self._close_review_window()
        self.start_button.configure(state="normal", text="시작")
        self.cancel_button.configure(state="disabled", text="강제 종료")
        self.status_label.configure(text=message)

    def add_manual_ocr_box_to_review(self, text: str, box: tuple[int, int, int, int]) -> tuple[Path, str]:
        if self.current_ocr_review is None or self.current_settings is None:
            raise RuntimeError("OCR 검수 정보가 없습니다.")
        left, top, width, height = box
        self.current_ocr_review = add_manual_ocr_box(
            self.current_ocr_review,
            self.current_settings,
            text=text,
            left=left,
            top=top,
            width=width,
            height=height,
        )
        self._update_progress(
            (self.current_index + 0.35) / max(1, len(self.selected_images)),
            f"OCR 수동 추가: {text}",
        )
        return self.current_ocr_review.preview_path, format_ocr_review_text(self.current_ocr_review.boxes)

    def delete_ocr_box_from_review(self, index: int) -> tuple[Path, str]:
        if self.current_ocr_review is None or self.current_settings is None:
            raise RuntimeError("OCR 검수 정보가 없습니다.")
        removed_text = self.current_ocr_review.boxes[index].text if 0 <= index < len(self.current_ocr_review.boxes) else ""
        self.current_ocr_review = delete_ocr_box(self.current_ocr_review, self.current_settings, index=index)
        if removed_text:
            self._update_progress(
                (self.current_index + 0.35) / max(1, len(self.selected_images)),
                f"OCR 삭제: {removed_text}",
            )
        return self.current_ocr_review.preview_path, format_ocr_review_text(self.current_ocr_review.boxes)

    def _open_review_window(self, *, title: str, image_path: Path, body: str, add_box_command=None, delete_box_command=None) -> None:
        self._close_review_window()
        self.review_window = ImageTranslationReviewWindow(
            self,
            title=title,
            image_path=image_path,
            body=body,
            approve_command=self.approve_current_stage,
            reject_command=self.reject_current_stage,
            add_box_command=add_box_command,
            delete_box_command=delete_box_command,
        )
        self.review_window.focus()

    def _close_review_window(self) -> None:
        if self.review_window is None:
            return
        if self.review_window.winfo_exists():
            self.review_window.destroy()
        self.review_window = None

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
            translation_provider=self._translation_provider(),
        )

    def _translation_provider(self) -> str:
        if self.translation_provider_menu.get() == "DeepL 무료 API":
            return "deepl"
        return "local"

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
