from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def initialize_database(self) -> Path:
        ...
