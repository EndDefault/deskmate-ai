from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "DeskMate AI"
    ollama_base_url: str = os.getenv("DESKMATE_OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("DESKMATE_OLLAMA_MODEL", "qwen3:4b")
    ollama_timeout_seconds: float = float(os.getenv("DESKMATE_OLLAMA_TIMEOUT_SECONDS", "15"))
    ollama_keep_alive: str = os.getenv("DESKMATE_OLLAMA_KEEP_ALIVE", "10m")
    ollama_max_tokens: int = int(os.getenv("DESKMATE_OLLAMA_MAX_TOKENS", "512"))
    document_preview_chars: int = int(os.getenv("DESKMATE_DOCUMENT_PREVIEW_CHARS", "1200"))
    data_dir: Path = Path(os.getenv("DESKMATE_DATA_DIR", Path.home() / ".deskmate_ai"))
    database_path: Path | None = None

    @property
    def resolved_database_path(self) -> Path:
        if self.database_path is not None:
            return self.database_path
        return self.data_dir / "deskmate.db"


DEFAULT_CONFIG = AppConfig()
