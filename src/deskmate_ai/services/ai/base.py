from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    def ask(self, prompt: str) -> str | None:
        ...
