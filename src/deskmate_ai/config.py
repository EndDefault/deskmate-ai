from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "DeskMate AI"
    ollama_base_url: str = os.getenv("DESKMATE_OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("DESKMATE_OLLAMA_MODEL", "qwen3:4b")
    document_preview_chars: int = int(os.getenv("DESKMATE_DOCUMENT_PREVIEW_CHARS", "1200"))


DEFAULT_CONFIG = AppConfig()
