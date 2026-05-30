from __future__ import annotations

from threading import Thread
from tkinter import filedialog

import customtkinter as ctk

from deskmate_ai.config import DEFAULT_CONFIG
from deskmate_ai.core.assistant import handle_prompt
from deskmate_ai.services.speech_service import speak
from deskmate_ai.ui import layout
from deskmate_ai.ui.windows import CacheManagerWindow, ImageTranslationWindow


class DeskMateApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(DEFAULT_CONFIG.app_name)
        self.geometry("940x640")

        self.tts_enabled = ctk.BooleanVar(value=False)
        self.document_path: str | None = None
        self.is_processing = False
        self.cache_category_vars: dict[int, ctk.BooleanVar] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=208)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        self.sidebar.grid_propagate(False)

        layout.build_chat_area(self)
        self._build_sidebar()

    def _build_sidebar(self) -> None:
        layout.build_sidebar(self)

    def active_cache_category_ids(self) -> list[int]:
        return [category_id for category_id, var in self.cache_category_vars.items() if var.get()]

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
            args=(prompt, self.document_path, self.active_cache_category_ids()),
            daemon=True,
        ).start()

    def _process_prompt(
        self,
        prompt: str,
        document_path: str | None,
        cache_category_ids: list[int],
    ) -> None:
        result = handle_prompt(
            prompt,
            document_path=document_path,
            cache_category_ids=cache_category_ids,
        )
        self.after(0, self._finish_prompt, result.message)

    def _finish_prompt(self, message: str) -> None:
        self._set_processing(False)
        self._append_message("AI", message)

        if self.tts_enabled.get():
            Thread(target=speak, args=(message,), daemon=True).start()

    def show_cache_list(self) -> None:
        window = CacheManagerWindow(self, on_change=self._build_sidebar)
        window.focus()

    def show_image_translation(self) -> None:
        window = ImageTranslationWindow(self)
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


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = DeskMateApp()
    app.mainloop()
