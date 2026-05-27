from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from deskmate_ai.config import DEFAULT_CONFIG
from deskmate_ai.core.assistant import handle_prompt
from deskmate_ai.services.speech_service import speak


class DeskMateApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(DEFAULT_CONFIG.app_name)
        self.geometry("640x480")

        self.tts_enabled = ctk.BooleanVar(value=False)
        self.document_path: str | None = None

        self.chat_log = ctk.CTkTextbox(self, wrap="word")
        self.chat_log.pack(fill="both", expand=True, padx=16, pady=(16, 8))

        document_bar = ctk.CTkFrame(self)
        document_bar.pack(fill="x", padx=16, pady=(0, 8))

        self.document_label = ctk.CTkLabel(document_bar, text="선택된 문서 없음", anchor="w")
        self.document_label.pack(side="left", fill="x", expand=True, padx=8, pady=8)

        document_button = ctk.CTkButton(
            document_bar,
            text="문서 선택",
            width=96,
            command=self.select_document,
        )
        document_button.pack(side="left", padx=(0, 8), pady=8)

        controls = ctk.CTkFrame(self)
        controls.pack(fill="x", padx=16, pady=(0, 16))

        self.prompt_entry = ctk.CTkEntry(controls, placeholder_text="명령을 입력하세요")
        self.prompt_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=8)
        self.prompt_entry.bind("<Return>", lambda _: self.submit_prompt())

        tts_toggle = ctk.CTkSwitch(controls, text="TTS", variable=self.tts_enabled)
        tts_toggle.pack(side="left", padx=(0, 8), pady=8)

        submit_button = ctk.CTkButton(controls, text="전송", width=72, command=self.submit_prompt)
        submit_button.pack(side="left", padx=(0, 8), pady=8)

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
        prompt = self.prompt_entry.get()
        self.prompt_entry.delete(0, "end")

        self._append_message("User", prompt)
        result = handle_prompt(prompt, document_path=self.document_path)
        self._append_message("AI", result.message)

        if self.tts_enabled.get():
            speak(result.message)

    def _append_message(self, sender: str, message: str) -> None:
        self.chat_log.insert("end", f"{sender}: {message}\n\n")
        self.chat_log.see("end")


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = DeskMateApp()
    app.mainloop()
