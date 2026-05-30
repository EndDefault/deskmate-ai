from __future__ import annotations

import customtkinter as ctk

from deskmate_ai.ui import theme, widgets


class BaseWindow(ctk.CTkToplevel):
    def __init__(self, parent, *, title: str, geometry: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(geometry)
        self.transient(parent)
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=theme.PADDING_WINDOW, pady=theme.PADDING_WINDOW)

    def clear(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def header(self, title: str, *, back_command=None, action_button=None) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        if back_command is not None:
            widgets.back_button(header, back_command).pack(side="left")
        widgets.title_label(header, title).pack(side="left", padx=12 if back_command else 0)
        if action_button is not None:
            action_button(header).pack(side="right")
        return header
