from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
