from __future__ import annotations

import customtkinter as ctk


COLOR_DANGER = "#7f1d1d"
COLOR_DANGER_HOVER = "#991b1b"
COLOR_LIST_HOVER = "#2f3a4a"
COLOR_ERROR = "#f87171"

BUTTON_WIDTH_ICON = 36
BUTTON_WIDTH_SM = 72
BUTTON_WIDTH_MD = 96
BUTTON_WIDTH_LG = 120

PADDING_WINDOW = 16
PADDING_APP_X = 12
PADDING_APP_Y = 12


def title_font(size: int = 18) -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight="bold")
