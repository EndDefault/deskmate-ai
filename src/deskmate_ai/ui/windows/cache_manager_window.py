from __future__ import annotations

import customtkinter as ctk

from deskmate_ai.services.storage_service import (
    KeywordCache,
    KeywordCacheCategory,
    delete_keyword_cache,
    get_keyword_cache,
    get_keyword_cache_category,
    list_keyword_cache_categories,
    list_keyword_caches,
    save_keyword_cache,
    save_keyword_cache_category,
)
from deskmate_ai.ui import theme, widgets
from deskmate_ai.ui.constants import ACTION_LABELS, ACTION_VALUES
from deskmate_ai.ui.windows.base_window import BaseWindow


class CacheManagerWindow(BaseWindow):
    def __init__(self, parent, *, on_change) -> None:
        super().__init__(parent, title="캐시 관리", geometry="640x580")
        self.on_change = on_change
        self.show_categories()

    def show_categories(self) -> None:
        self.clear()
        self.header(
            "전체 캐시 보기",
            action_button=lambda parent: widgets.primary_button(
                parent,
                "카테고리 추가",
                width=theme.BUTTON_WIDTH_LG,
                command=self.show_category_form,
            ),
        )

        list_frame = ctk.CTkScrollableFrame(self.container)
        list_frame.pack(fill="both", expand=True)
        for category in list_keyword_cache_categories():
            self._add_category_row(list_frame, category)

    def show_category_form(self, category: KeywordCacheCategory | None = None) -> None:
        self.clear()
        self.header("카테고리 수정" if category else "카테고리 추가", back_command=self.show_categories)

        ctk.CTkLabel(self.container, text="카테고리 이름", anchor="w").pack(fill="x", pady=(8, 4))
        name_entry = ctk.CTkEntry(self.container, placeholder_text="예: 업무 캐시")
        name_entry.pack(fill="x", pady=(0, 12))
        if category:
            name_entry.insert(0, category.name)

        status_label = widgets.status_label(self.container)
        status_label.pack(fill="x", pady=(0, 8))
        widgets.primary_button(
            self.container,
            "저장",
            command=lambda: self._save_category(category, name_entry, status_label),
        ).pack(anchor="e")

    def show_category_detail(self, category_id: int) -> None:
        category = get_keyword_cache_category(category_id)
        if category is None:
            self.show_categories()
            return

        self.clear()
        self.header(
            category.name,
            back_command=self.show_categories,
            action_button=lambda parent: widgets.primary_button(
                parent,
                "캐시 추가",
                width=theme.BUTTON_WIDTH_MD,
                command=lambda: self.show_cache_form(category.id),
            ),
        )

        caches = list_keyword_caches(category_id=category.id)
        if not caches:
            ctk.CTkLabel(self.container, text="이 카테고리에 저장된 캐시가 없습니다.").pack(fill="both", expand=True)
            return

        list_frame = ctk.CTkScrollableFrame(self.container)
        list_frame.pack(fill="both", expand=True)
        for cache in caches:
            self._add_cache_row(list_frame, cache)

    def show_cache_detail(self, cache_id: int) -> None:
        cache = get_keyword_cache(cache_id)
        if cache is None:
            self.show_categories()
            return

        category = get_keyword_cache_category(cache.category_id)
        self.clear()
        self.header(
            cache.keyword,
            back_command=lambda: self.show_category_detail(cache.category_id),
            action_button=lambda parent: widgets.primary_button(
                parent,
                "수정",
                width=theme.BUTTON_WIDTH_SM,
                command=lambda: self.show_cache_form(cache.category_id, cache),
            ),
        )

        ctk.CTkLabel(
            self.container,
            text=f"카테고리: {category.name if category else cache.category_id}",
            anchor="w",
        ).pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            self.container,
            text=f"액션: {ACTION_LABELS.get(cache.action_type, cache.action_type)}",
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        content = ctk.CTkTextbox(self.container, wrap="word")
        content.pack(fill="both", expand=True)
        content.insert("end", cache.content)
        content.configure(state="disabled")

    def show_cache_form(self, category_id: int, cache: KeywordCache | None = None) -> None:
        self.clear()
        self.header("캐시 수정" if cache else "캐시 추가", back_command=lambda: self.show_category_detail(category_id))

        ctk.CTkLabel(self.container, text="키워드", anchor="w").pack(fill="x", pady=(8, 4))
        keyword_entry = ctk.CTkEntry(self.container, placeholder_text="예: 아카라이브")
        keyword_entry.pack(fill="x", pady=(0, 12))
        if cache:
            keyword_entry.insert(0, cache.keyword)

        ctk.CTkLabel(self.container, text="액션 종류", anchor="w").pack(fill="x", pady=(0, 4))
        current_action = ACTION_LABELS.get(cache.action_type, ACTION_LABELS["show_text"]) if cache else ACTION_LABELS["show_text"]
        action_menu = ctk.CTkOptionMenu(self.container, values=list(ACTION_VALUES.keys()))
        action_menu.set(current_action)
        action_menu.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(self.container, text="내용", anchor="w").pack(fill="x", pady=(0, 4))
        content_box = ctk.CTkTextbox(self.container, wrap="word", height=220)
        content_box.pack(fill="both", expand=True, pady=(0, 12))
        if cache:
            content_box.insert("end", cache.content)

        status_label = widgets.status_label(self.container)
        status_label.pack(fill="x", pady=(0, 8))
        widgets.primary_button(
            self.container,
            "저장",
            command=lambda: self._save_cache(category_id, cache, keyword_entry, action_menu, content_box, status_label),
        ).pack(anchor="e")

    def confirm_delete_cache(self, cache: KeywordCache) -> None:
        dialog = BaseWindow(self, title="캐시 삭제 확인", geometry="420x320")
        dialog.grab_set()
        widgets.title_label(dialog.container, "정말 삭제할까요?").pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(dialog.container, text=f"키워드: {cache.keyword}", anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            dialog.container,
            text=f"액션: {ACTION_LABELS.get(cache.action_type, cache.action_type)}",
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        content = ctk.CTkTextbox(dialog.container, wrap="word", height=120)
        content.pack(fill="both", expand=True, pady=(0, 12))
        content.insert("end", cache.content)
        content.configure(state="disabled")
        actions = ctk.CTkFrame(dialog.container, fg_color="transparent")
        actions.pack(fill="x")
        widgets.primary_button(actions, "취소", command=dialog.destroy).pack(side="right")
        widgets.danger_button(actions, "삭제", command=lambda: self._delete_cache_and_close(cache, dialog)).pack(
            side="right", padx=(0, 8)
        )

    def _add_category_row(self, parent: ctk.CTkFrame, category: KeywordCacheCategory) -> None:
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=(0, 8))
        count = len(list_keyword_caches(category_id=category.id))
        widgets.list_action_button(
            row,
            f"{category.name}  |  {count}",
            command=lambda category_id=category.id: self.show_category_detail(category_id),
        ).pack(side="left", fill="x", expand=True, padx=(8, 8), pady=8)
        widgets.primary_button(row, "수정", width=64, command=lambda item=category: self.show_category_form(item)).pack(
            side="left", padx=(0, 8), pady=8
        )

    def _add_cache_row(self, parent: ctk.CTkFrame, cache: KeywordCache) -> None:
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=(0, 8))
        label = f"{cache.keyword}  |  {ACTION_LABELS.get(cache.action_type, cache.action_type)}"
        widgets.list_action_button(row, label, command=lambda cache_id=cache.id: self.show_cache_detail(cache_id)).pack(
            side="left", fill="x", expand=True, padx=(8, 8), pady=8
        )
        widgets.primary_button(
            row,
            "수정",
            width=64,
            command=lambda item=cache: self.show_cache_form(item.category_id, item),
        ).pack(side="left", padx=(0, 8), pady=8)
        widgets.danger_button(
            row,
            "x",
            width=theme.BUTTON_WIDTH_ICON,
            command=lambda item=cache: self.confirm_delete_cache(item),
        ).pack(side="left", padx=(0, 8), pady=8)

    def _save_category(
        self,
        category: KeywordCacheCategory | None,
        name_entry: ctk.CTkEntry,
        status_label: ctk.CTkLabel,
    ) -> None:
        name = name_entry.get().strip()
        if not name:
            status_label.configure(text="카테고리 이름을 입력해 주세요.")
            return
        save_keyword_cache_category(name, category_id=None if category is None else category.id)
        self.on_change()
        self.show_categories()

    def _save_cache(
        self,
        category_id: int,
        cache: KeywordCache | None,
        keyword_entry: ctk.CTkEntry,
        action_menu: ctk.CTkOptionMenu,
        content_box: ctk.CTkTextbox,
        status_label: ctk.CTkLabel,
    ) -> None:
        keyword = keyword_entry.get().strip()
        content = content_box.get("1.0", "end").strip()
        if not keyword or not content:
            status_label.configure(text="키워드와 내용을 모두 입력해 주세요.")
            return
        save_keyword_cache(
            keyword,
            content,
            category_id=category_id,
            action_type=ACTION_VALUES[action_menu.get()],
            cache_id=None if cache is None else cache.id,
        )
        self.on_change()
        self.show_category_detail(category_id)

    def _delete_cache_and_close(self, cache: KeywordCache, dialog: ctk.CTkToplevel) -> None:
        delete_keyword_cache(cache.id)
        dialog.destroy()
        self.on_change()
        self.show_category_detail(cache.category_id)
