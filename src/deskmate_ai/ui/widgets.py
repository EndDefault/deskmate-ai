from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from deskmate_ai.ui import theme


def title_label(parent, text: str, *, size: int = 18, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=theme.title_font(size), **kwargs)


def primary_button(parent, text: str, command: Callable | None = None, **kwargs) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, **kwargs)


def back_button(parent, command: Callable, *, text: str = "되돌아가기") -> ctk.CTkButton:
    return primary_button(parent, text=text, width=theme.BUTTON_WIDTH_MD, command=command)


def danger_button(parent, text: str, command: Callable | None = None, **kwargs) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=theme.COLOR_DANGER,
        hover_color=theme.COLOR_DANGER_HOVER,
        **kwargs,
    )


def status_label(parent, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text="", text_color=theme.COLOR_ERROR, **kwargs)


def list_action_button(parent, text: str, command: Callable, **kwargs) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        anchor="w",
        fg_color="transparent",
        hover_color=theme.COLOR_LIST_HOVER,
        command=command,
        **kwargs,
    )
