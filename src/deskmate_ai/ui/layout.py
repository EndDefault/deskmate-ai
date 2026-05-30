from __future__ import annotations

import customtkinter as ctk

from deskmate_ai.config import DEFAULT_CONFIG
from deskmate_ai.services.storage_service import list_keyword_cache_categories


def build_chat_area(app) -> None:
    app.chat_log = ctk.CTkTextbox(app.main, wrap="word")
    app.chat_log.grid(row=0, column=0, sticky="nsew")

    controls = ctk.CTkFrame(app.main)
    controls.grid(row=1, column=0, sticky="ew", pady=(8, 0))
    controls.grid_columnconfigure(0, weight=1)

    app.prompt_entry = ctk.CTkEntry(controls, placeholder_text="Enter a command")
    app.prompt_entry.grid(row=0, column=0, sticky="ew", padx=(8, 8), pady=8)
    app.prompt_entry.bind("<Return>", lambda _: app.submit_prompt())

    app.submit_button = ctk.CTkButton(controls, text="Send", width=72, command=app.submit_prompt)
    app.submit_button.grid(row=0, column=1, padx=(0, 8), pady=8)


def build_sidebar(app) -> None:
    for child in app.sidebar.winfo_children():
        child.destroy()

    title = ctk.CTkLabel(app.sidebar, text=DEFAULT_CONFIG.app_name, font=ctk.CTkFont(size=18, weight="bold"))
    title.pack(fill="x", padx=12, pady=(16, 12))

    ctk.CTkLabel(app.sidebar, text="Cache", anchor="w", font=ctk.CTkFont(weight="bold")).pack(
        fill="x", padx=12, pady=(8, 4)
    )
    ctk.CTkButton(app.sidebar, text="Manage cache", command=app.show_cache_list).pack(
        fill="x", padx=12, pady=(0, 8)
    )
    ctk.CTkButton(app.sidebar, text="Refresh cache list", command=app._build_sidebar).pack(
        fill="x", padx=12, pady=(0, 8)
    )

    ctk.CTkLabel(app.sidebar, text="Prompt categories", anchor="w").pack(fill="x", padx=12, pady=(4, 2))
    category_frame = ctk.CTkScrollableFrame(app.sidebar, height=120)
    category_frame.pack(fill="x", padx=12, pady=(0, 12))
    app.cache_category_vars.clear()
    for category in list_keyword_cache_categories():
        var = ctk.BooleanVar(value=True)
        app.cache_category_vars[category.id] = var
        ctk.CTkCheckBox(category_frame, text=category.name, variable=var).pack(fill="x", pady=2)

    ctk.CTkLabel(app.sidebar, text="Document", anchor="w", font=ctk.CTkFont(weight="bold")).pack(
        fill="x", padx=12, pady=(8, 4)
    )
    ctk.CTkButton(app.sidebar, text="Select document", command=app.select_document).pack(
        fill="x", padx=12, pady=(0, 8)
    )
    app.document_label = ctk.CTkLabel(app.sidebar, text="No document selected", anchor="w", wraplength=170, justify="left")
    app.document_label.pack(fill="x", padx=12, pady=(0, 12))

    ctk.CTkLabel(app.sidebar, text="Image translation", anchor="w", font=ctk.CTkFont(weight="bold")).pack(
        fill="x", padx=12, pady=(8, 4)
    )
    ctk.CTkButton(app.sidebar, text="Open translation", command=app.show_image_translation).pack(
        fill="x", padx=12, pady=(0, 12)
    )

    ctk.CTkFrame(app.sidebar, fg_color="transparent").pack(fill="both", expand=True)
    ctk.CTkSwitch(app.sidebar, text="TTS", variable=app.tts_enabled).pack(fill="x", padx=12, pady=(0, 16))
