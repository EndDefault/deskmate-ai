from __future__ import annotations

from deskmate_ai.config import DEFAULT_CONFIG, AppConfig
from deskmate_ai.storage.models import Memo
from deskmate_ai.storage.sqlite.connection import connect, utc_now
from deskmate_ai.storage.sqlite.schema import initialize_database


def add_memo(content: str, *, config: AppConfig = DEFAULT_CONFIG) -> Memo:
    initialize_database(config=config)
    now = utc_now()
    with connect(config.resolved_database_path) as connection:
        cursor = connection.execute("INSERT INTO memos(content, created_at) VALUES (?, ?)", (content, now))
        memo_id = int(cursor.lastrowid)
    return Memo(id=memo_id, content=content, created_at=now)


def list_recent_memos(limit: int = 5, *, config: AppConfig = DEFAULT_CONFIG) -> list[Memo]:
    initialize_database(config=config)
    with connect(config.resolved_database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, content, created_at
            FROM memos
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [Memo(id=int(row["id"]), content=str(row["content"]), created_at=str(row["created_at"])) for row in rows]
