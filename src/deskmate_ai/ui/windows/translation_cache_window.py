from __future__ import annotations

import customtkinter as ctk

from deskmate_ai.services.storage_service import (
    TranslationCacheGroup,
    TranslationTerm,
    delete_translation_cache_group,
    delete_translation_term,
    get_translation_cache_group,
    list_translation_cache_groups,
    list_translation_terms,
    save_translation_cache_group,
    save_translation_term,
)
from deskmate_ai.ui import theme, widgets
from deskmate_ai.ui.constants import LANGUAGE_NAMES, SOURCE_LANGUAGES, TARGET_LANGUAGES
from deskmate_ai.ui.windows.base_window import BaseWindow


class TranslationCacheWindow(BaseWindow):
    def __init__(self, parent, *, on_change) -> None:
        super().__init__(parent, title="번역용 캐시", geometry="760x640")
        self.on_change = on_change
        self.language_filter = ctk.StringVar(value="전체")
        self.show_groups()

    def show_groups(self) -> None:
        self.clear()
        self.header(
            "번역용 캐시",
            action_button=lambda parent: widgets.primary_button(
                parent,
                "캐시 추가",
                width=theme.BUTTON_WIDTH_LG,
                command=self.show_group_form,
            ),
        )

        list_frame = ctk.CTkScrollableFrame(self.container)
        list_frame.pack(fill="both", expand=True)
        for group in list_translation_cache_groups():
            self._add_group_row(list_frame, group)

    def show_group_form(self, group: TranslationCacheGroup | None = None) -> None:
        self.clear()
        self.header("번역 캐시 수정" if group else "번역 캐시 추가", back_command=self.show_groups)

        ctk.CTkLabel(self.container, text="캐시 이름", anchor="w").pack(fill="x", pady=(8, 4))
        name_entry = ctk.CTkEntry(self.container, placeholder_text="예: 만화 상황 캐시")
        name_entry.pack(fill="x", pady=(0, 12))
        if group:
            name_entry.insert(0, group.name)

        controls = ctk.CTkFrame(self.container)
        controls.pack(fill="x", pady=(0, 12))
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(controls, text="원문 언어").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        source_menu = ctk.CTkOptionMenu(controls, values=list(SOURCE_LANGUAGES.keys()))
        source_menu.set(LANGUAGE_NAMES.get(group.source_language, "영어") if group else "영어")
        source_menu.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

        ctk.CTkLabel(controls, text="번역 언어").grid(row=0, column=2, padx=8, pady=8, sticky="w")
        target_menu = ctk.CTkOptionMenu(controls, values=list(TARGET_LANGUAGES.keys()))
        target_menu.set(LANGUAGE_NAMES.get(group.target_language, "한국어") if group else "한국어")
        target_menu.grid(row=0, column=3, padx=8, pady=8, sticky="ew")

        status_label = widgets.status_label(self.container)
        status_label.pack(fill="x", pady=(0, 8))
        widgets.primary_button(
            self.container,
            "저장",
            command=lambda: self._save_group(group, name_entry, source_menu, target_menu, status_label),
        ).pack(anchor="e")

    def show_group_detail(self, group_id: int) -> None:
        group = get_translation_cache_group(group_id)
        if group is None:
            self.show_groups()
            return

        self.clear()
        self.header(
            group.name,
            back_command=self.show_groups,
            action_button=lambda parent: widgets.primary_button(
                parent,
                "용어 추가",
                width=theme.BUTTON_WIDTH_MD,
                command=lambda: self.show_term_form(group),
            ),
        )

        filter_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        filter_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(filter_frame, text="언어 필터", anchor="w").pack(side="left", padx=(0, 8))
        filter_values = ["전체", self._language_pair_label(group.source_language, group.target_language)]
        filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=filter_values,
            variable=self.language_filter,
            command=lambda _: self.show_group_detail(group.id),
        )
        if self.language_filter.get() not in filter_values:
            self.language_filter.set("전체")
        filter_menu.pack(side="left")

        terms = self._filtered_terms(group)
        if not terms:
            ctk.CTkLabel(self.container, text="저장된 번역 용어가 없습니다.").pack(fill="both", expand=True)
            return

        list_frame = ctk.CTkScrollableFrame(self.container)
        list_frame.pack(fill="both", expand=True)
        for term in terms:
            self._add_term_row(list_frame, group, term)

    def show_term_form(self, group: TranslationCacheGroup, term: TranslationTerm | None = None) -> None:
        self.clear()
        self.header("용어 수정" if term else "용어 추가", back_command=lambda: self.show_group_detail(group.id))

        ctk.CTkLabel(self.container, text="원문", anchor="w").pack(fill="x", pady=(8, 4))
        source_entry = ctk.CTkEntry(self.container, placeholder_text="예: Start Game")
        source_entry.pack(fill="x", pady=(0, 12))
        if term:
            source_entry.insert(0, term.source_text)

        ctk.CTkLabel(self.container, text="번역", anchor="w").pack(fill="x", pady=(0, 4))
        translated_entry = ctk.CTkEntry(self.container, placeholder_text="예: 게임 시작")
        translated_entry.pack(fill="x", pady=(0, 12))
        if term:
            translated_entry.insert(0, term.translated_text)

        ctk.CTkLabel(self.container, text="메모", anchor="w").pack(fill="x", pady=(0, 4))
        note_box = ctk.CTkTextbox(self.container, wrap="word", height=120)
        note_box.pack(fill="both", expand=True, pady=(0, 12))
        if term:
            note_box.insert("end", term.note)

        status_label = widgets.status_label(self.container)
        status_label.pack(fill="x", pady=(0, 8))
        widgets.primary_button(
            self.container,
            "저장",
            command=lambda: self._save_term(group, term, source_entry, translated_entry, note_box, status_label),
        ).pack(anchor="e")

    def _add_group_row(self, parent: ctk.CTkFrame, group: TranslationCacheGroup) -> None:
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=(0, 8))
        label = f"{group.name}  |  {self._language_pair_label(group.source_language, group.target_language)}"
        widgets.list_action_button(row, label, command=lambda group_id=group.id: self.show_group_detail(group_id)).pack(
            side="left", fill="x", expand=True, padx=(8, 8), pady=8
        )
        widgets.primary_button(row, "수정", width=64, command=lambda item=group: self.show_group_form(item)).pack(
            side="left", padx=(0, 8), pady=8
        )
        widgets.danger_button(
            row,
            "x",
            width=theme.BUTTON_WIDTH_ICON,
            command=lambda group_id=group.id: self._delete_group(group_id),
        ).pack(side="left", padx=(0, 8), pady=8)

    def _add_term_row(self, parent: ctk.CTkFrame, group: TranslationCacheGroup, term: TranslationTerm) -> None:
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=(0, 8))
        label = f"{term.source_text}  →  {term.translated_text}"
        widgets.list_action_button(row, label, command=lambda item=term: self.show_term_form(group, item)).pack(
            side="left", fill="x", expand=True, padx=(8, 8), pady=8
        )
        widgets.primary_button(row, "수정", width=64, command=lambda item=term: self.show_term_form(group, item)).pack(
            side="left", padx=(0, 8), pady=8
        )
        widgets.danger_button(
            row,
            "x",
            width=theme.BUTTON_WIDTH_ICON,
            command=lambda term_id=term.id: self._delete_term(group.id, term_id),
        ).pack(side="left", padx=(0, 8), pady=8)

    def _save_group(self, group, name_entry, source_menu, target_menu, status_label) -> None:
        name = name_entry.get().strip()
        if not name:
            status_label.configure(text="캐시 이름을 입력해 주세요.")
            return
        save_translation_cache_group(
            name,
            SOURCE_LANGUAGES[source_menu.get()],
            TARGET_LANGUAGES[target_menu.get()],
            group_id=None if group is None else group.id,
        )
        self.on_change()
        self.show_groups()

    def _save_term(self, group, term, source_entry, translated_entry, note_box, status_label) -> None:
        source_text = source_entry.get().strip()
        translated_text = translated_entry.get().strip()
        if not source_text or not translated_text:
            status_label.configure(text="원문과 번역을 모두 입력해 주세요.")
            return
        save_translation_term(
            group.id,
            group.source_language,
            group.target_language,
            source_text,
            translated_text,
            note=note_box.get("1.0", "end").strip(),
            term_id=None if term is None else term.id,
        )
        self.show_group_detail(group.id)

    def _delete_group(self, group_id: int) -> None:
        delete_translation_cache_group(group_id)
        self.on_change()
        self.show_groups()

    def _delete_term(self, group_id: int, term_id: int) -> None:
        delete_translation_term(term_id)
        self.show_group_detail(group_id)

    def _filtered_terms(self, group: TranslationCacheGroup) -> list[TranslationTerm]:
        if self.language_filter.get() == "전체":
            return list_translation_terms(group_id=group.id)
        return list_translation_terms(
            group_id=group.id,
            source_language=group.source_language,
            target_language=group.target_language,
        )

    def _language_pair_label(self, source_language: str, target_language: str) -> str:
        source = LANGUAGE_NAMES.get(source_language, source_language)
        target = LANGUAGE_NAMES.get(target_language, target_language)
        return f"{source} -> {target}"
