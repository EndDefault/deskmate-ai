from __future__ import annotations

import customtkinter as ctk

from .assistant import handle_prompt
from .speech import speak


class DeskMateApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DeskMate AI")
        self.geometry("520x420")

        self.tts_enabled = ctk.BooleanVar(value=False)

        self.chat_log = ctk.CTkTextbox(self, wrap="word")
        self.chat_log.pack(fill="both", expand=True, padx=16, pady=(16, 8))

        controls = ctk.CTkFrame(self)
        controls.pack(fill="x", padx=16, pady=(0, 16))

        self.prompt_entry = ctk.CTkEntry(controls, placeholder_text="명령을 입력하세요")
        self.prompt_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=8)
        self.prompt_entry.bind("<Return>", lambda _: self.submit_prompt())

        tts_toggle = ctk.CTkSwitch(controls, text="TTS", variable=self.tts_enabled)
        tts_toggle.pack(side="left", padx=(0, 8), pady=8)

        submit_button = ctk.CTkButton(controls, text="전송", width=72, command=self.submit_prompt)
        submit_button.pack(side="left", padx=(0, 8), pady=8)

    def submit_prompt(self) -> None:
        prompt = self.prompt_entry.get()
        self.prompt_entry.delete(0, "end")

        self._append_message("User", prompt)
        result = handle_prompt(prompt)
        self._append_message("AI", result.message)

        if self.tts_enabled.get():
            speak(result.message)

    def _append_message(self, sender: str, message: str) -> None:
        self.chat_log.insert("end", f"{sender}: {message}\n\n")
        self.chat_log.see("end")


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = DeskMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
