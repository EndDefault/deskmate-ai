from __future__ import annotations

from threading import Thread
from tkinter import filedialog

import customtkinter as ctk

from deskmate_ai.config import DEFAULT_CONFIG
from deskmate_ai.core.assistant import handle_prompt
from deskmate_ai.services.speech_service import speak
from deskmate_ai.services.storage_service import (
    KeywordCache,
    delete_keyword_cache,
    get_keyword_cache,
    list_keyword_caches,
    save_keyword_cache,
)


ACTION_LABELS = {
    "show_text": "내용 보여주기",
    "open_url": "사이트 열기",
}
ACTION_VALUES = {label: value for value, label in ACTION_LABELS.items()}


class DeskMateApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(DEFAULT_CONFIG.app_name)
        self.geometry("920x620")

        self.tts_enabled = ctk.BooleanVar(value=False)
        self.document_path: str | None = None
        self.is_processing = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=184)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        self.sidebar.grid_propagate(False)

        self._build_chat_area()
        self._build_sidebar()

    def _build_chat_area(self) -> None:
        self.chat_log = ctk.CTkTextbox(self.main, wrap="word")
        self.chat_log.grid(row=0, column=0, sticky="nsew")

        controls = ctk.CTkFrame(self.main)
        controls.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        controls.grid_columnconfigure(0, weight=1)

        self.prompt_entry = ctk.CTkEntry(controls, placeholder_text="명령을 입력하세요")
        self.prompt_entry.grid(row=0, column=0, sticky="ew", padx=(8, 8), pady=8)
        self.prompt_entry.bind("<Return>", lambda _: self.submit_prompt())

        self.submit_button = ctk.CTkButton(
            controls,
            text="전송",
            width=72,
            command=self.submit_prompt,
        )
        self.submit_button.grid(row=0, column=1, padx=(0, 8), pady=8)

    def _build_sidebar(self) -> None:
        title = ctk.CTkLabel(self.sidebar, text="DeskMate", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(fill="x", padx=12, pady=(16, 12))

        cache_label = ctk.CTkLabel(self.sidebar, text="캐시", anchor="w", font=ctk.CTkFont(weight="bold"))
        cache_label.pack(fill="x", padx=12, pady=(8, 4))

        cache_list_button = ctk.CTkButton(self.sidebar, text="전체 캐시 보기", command=self.show_cache_list)
        cache_list_button.pack(fill="x", padx=12, pady=(0, 12))

        doc_label = ctk.CTkLabel(self.sidebar, text="문서", anchor="w", font=ctk.CTkFont(weight="bold"))
        doc_label.pack(fill="x", padx=12, pady=(8, 4))

        doc_button = ctk.CTkButton(self.sidebar, text="문서 선택", command=self.select_document)
        doc_button.pack(fill="x", padx=12, pady=(0, 8))

        self.document_label = ctk.CTkLabel(
            self.sidebar,
            text="선택한 문서 없음",
            anchor="w",
            wraplength=150,
            justify="left",
        )
        self.document_label.pack(fill="x", padx=12, pady=(0, 12))

        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        tts_toggle = ctk.CTkSwitch(self.sidebar, text="TTS", variable=self.tts_enabled)
        tts_toggle.pack(fill="x", padx=12, pady=(0, 16))

    def select_document(self) -> None:
        path = filedialog.askopenfilename(
            title="요약할 문서 선택",
            filetypes=[
                ("Supported documents", "*.pdf *.txt *.md"),
                ("PDF files", "*.pdf"),
                ("Text files", "*.txt *.md"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        self.document_path = path
        self.document_label.configure(text=path)

    def submit_prompt(self) -> None:
        if self.is_processing:
            return

        prompt = self.prompt_entry.get()
        if not prompt.strip():
            return

        self.prompt_entry.delete(0, "end")
        self._append_message("User", prompt)
        self._set_processing(True)

        Thread(
            target=self._process_prompt,
            args=(prompt, self.document_path),
            daemon=True,
        ).start()

    def _process_prompt(self, prompt: str, document_path: str | None) -> None:
        result = handle_prompt(prompt, document_path=document_path)
        self.after(0, self._finish_prompt, result.message)

    def _finish_prompt(self, message: str) -> None:
        self._set_processing(False)
        self._append_message("AI", message)

        if self.tts_enabled.get():
            Thread(target=speak, args=(message,), daemon=True).start()

    def show_cache_list(self) -> None:
        window = CacheManagerWindow(self, mode="list")
        window.focus()

    def _append_message(self, sender: str, message: str) -> None:
        self.chat_log.insert("end", f"{sender}: {message}\n\n")
        self.chat_log.see("end")

    def _set_processing(self, processing: bool) -> None:
        self.is_processing = processing
        state = "disabled" if processing else "normal"
        text = "대기" if processing else "전송"
        self.prompt_entry.configure(state=state)
        self.submit_button.configure(state=state, text=text)


class CacheManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent: DeskMateApp, *, mode: str = "list") -> None:
        super().__init__(parent)
        self.title("캐시 관리")
        self.geometry("600x560")
        self.transient(parent)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=16, pady=16)

        if mode == "form":
            self.show_form()
        else:
            self.show_list()

    def show_list(self) -> None:
        self._clear()

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        title = ctk.CTkLabel(header, text="전체 캐시 보기", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(side="left")

        add_button = ctk.CTkButton(header, text="추가하기", width=88, command=self.show_form)
        add_button.pack(side="right")

        caches = list_keyword_caches()
        if not caches:
            empty = ctk.CTkLabel(self.container, text="저장된 캐시가 없습니다.")
            empty.pack(fill="both", expand=True)
            return

        list_frame = ctk.CTkScrollableFrame(self.container)
        list_frame.pack(fill="both", expand=True)
        for cache in caches:
            self._add_cache_row(list_frame, cache)

    def show_detail(self, cache_id: int) -> None:
        cache = get_keyword_cache(cache_id)
        if cache is None:
            self.show_list()
            return

        self._clear()
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        back_button = ctk.CTkButton(header, text="되돌아가기", width=96, command=self.show_list)
        back_button.pack(side="left")

        edit_button = ctk.CTkButton(
            header,
            text="수정",
            width=72,
            command=lambda: self.show_form(cache),
        )
        edit_button.pack(side="right")

        title = ctk.CTkLabel(
            self.container,
            text=cache.keyword,
            anchor="w",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(fill="x", pady=(0, 4))

        action_label = ctk.CTkLabel(
            self.container,
            text=f"액션: {ACTION_LABELS.get(cache.action_type, cache.action_type)}",
            anchor="w",
        )
        action_label.pack(fill="x", pady=(0, 8))

        content = ctk.CTkTextbox(self.container, wrap="word")
        content.pack(fill="both", expand=True)
        content.insert("end", cache.content)
        content.configure(state="disabled")

    def show_form(self, cache: KeywordCache | None = None) -> None:
        self._clear()

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        back_button = ctk.CTkButton(header, text="되돌아가기", width=96, command=self.show_list)
        back_button.pack(side="left")

        title_text = "캐시 수정" if cache else "캐시 추가"
        title = ctk.CTkLabel(header, text=title_text, font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(side="left", padx=12)

        keyword_label = ctk.CTkLabel(self.container, text="키워드", anchor="w")
        keyword_label.pack(fill="x", pady=(8, 4))

        keyword_entry = ctk.CTkEntry(self.container, placeholder_text="예: 아카라이브")
        keyword_entry.pack(fill="x", pady=(0, 12))
        if cache:
            keyword_entry.insert(0, cache.keyword)

        action_label = ctk.CTkLabel(self.container, text="액션 종류", anchor="w")
        action_label.pack(fill="x", pady=(0, 4))

        current_action = ACTION_LABELS.get(cache.action_type, ACTION_LABELS["show_text"]) if cache else ACTION_LABELS["show_text"]
        action_menu = ctk.CTkOptionMenu(
            self.container,
            values=list(ACTION_VALUES.keys()),
        )
        action_menu.set(current_action)
        action_menu.pack(fill="x", pady=(0, 12))

        content_label = ctk.CTkLabel(self.container, text="내용", anchor="w")
        content_label.pack(fill="x", pady=(0, 4))

        content_box = ctk.CTkTextbox(self.container, wrap="word", height=240)
        content_box.pack(fill="both", expand=True, pady=(0, 12))
        if cache:
            content_box.insert("end", cache.content)

        status_label = ctk.CTkLabel(self.container, text="", text_color="#f87171")
        status_label.pack(fill="x", pady=(0, 8))

        save_button = ctk.CTkButton(
            self.container,
            text="저장",
            command=lambda: self._save_cache(
                cache,
                keyword_entry,
                action_menu,
                content_box,
                status_label,
            ),
        )
        save_button.pack(anchor="e")

    def confirm_delete_cache(self, cache: KeywordCache) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("캐시 삭제 확인")
        dialog.geometry("420x320")
        dialog.transient(self)
        dialog.grab_set()

        title = ctk.CTkLabel(dialog, text="정말 삭제할까요?", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(fill="x", padx=16, pady=(16, 8))

        keyword = ctk.CTkLabel(dialog, text=f"키워드: {cache.keyword}", anchor="w")
        keyword.pack(fill="x", padx=16, pady=(0, 4))

        action = ctk.CTkLabel(
            dialog,
            text=f"액션: {ACTION_LABELS.get(cache.action_type, cache.action_type)}",
            anchor="w",
        )
        action.pack(fill="x", padx=16, pady=(0, 8))

        content = ctk.CTkTextbox(dialog, wrap="word", height=120)
        content.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        content.insert("end", cache.content)
        content.configure(state="disabled")

        actions = ctk.CTkFrame(dialog, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 16))

        cancel_button = ctk.CTkButton(actions, text="취소", command=dialog.destroy)
        cancel_button.pack(side="right")

        delete_button = ctk.CTkButton(
            actions,
            text="삭제",
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=lambda: self._delete_cache_and_close(cache.id, dialog),
        )
        delete_button.pack(side="right", padx=(0, 8))

    def _add_cache_row(self, parent: ctk.CTkFrame, cache: KeywordCache) -> None:
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=(0, 8))

        label = f"{cache.keyword}  |  {ACTION_LABELS.get(cache.action_type, cache.action_type)}"
        keyword_button = ctk.CTkButton(
            row,
            text=label,
            anchor="w",
            fg_color="transparent",
            hover_color="#2f3a4a",
            command=lambda cache_id=cache.id: self.show_detail(cache_id),
        )
        keyword_button.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=8)

        edit_button = ctk.CTkButton(
            row,
            text="수정",
            width=64,
            command=lambda item=cache: self.show_form(item),
        )
        edit_button.pack(side="left", padx=(0, 8), pady=8)

        delete_button = ctk.CTkButton(
            row,
            text="x",
            width=36,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=lambda item=cache: self.confirm_delete_cache(item),
        )
        delete_button.pack(side="left", padx=(0, 8), pady=8)

    def _save_cache(
        self,
        cache: KeywordCache | None,
        keyword_entry: ctk.CTkEntry,
        action_menu: ctk.CTkOptionMenu,
        content_box: ctk.CTkTextbox,
        status_label: ctk.CTkLabel,
    ) -> None:
        keyword = keyword_entry.get().strip()
        action_type = ACTION_VALUES[action_menu.get()]
        content = content_box.get("1.0", "end").strip()
        if not keyword or not content:
            status_label.configure(text="키워드와 내용을 모두 입력해 주세요.")
            return

        save_keyword_cache(
            keyword,
            content,
            action_type=action_type,
            cache_id=None if cache is None else cache.id,
        )
        self.show_list()

    def _delete_cache_and_close(self, cache_id: int, dialog: ctk.CTkToplevel) -> None:
        delete_keyword_cache(cache_id)
        dialog.destroy()
        self.show_list()

    def _clear(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = DeskMateApp()
    app.mainloop()
