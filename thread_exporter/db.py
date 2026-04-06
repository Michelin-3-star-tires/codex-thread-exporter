from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import MessageRecord, ThreadRecord, Transcript


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在：{path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_thread(row: sqlite3.Row) -> ThreadRecord:
    return ThreadRecord(**dict(row))


def search_threads(
    db_path: str | Path,
    keyword: str,
    field: str,
    limit: int = 20,
) -> list[ThreadRecord]:
    keyword = keyword.strip()
    if not keyword:
        return []

    field_map = {
        "id": "id",
        "title": "title",
        "first_user_message": "first_user_message",
    }
    if field not in field_map and field != "all":
        raise ValueError(f"不支持的检索字段：{field}")

    pattern = f"{keyword}%"
    with _connect(db_path) as conn:
        cur = conn.cursor()
        if field == "all":
            cur.execute(
                """
                SELECT *
                FROM threads
                WHERE id LIKE ? COLLATE NOCASE
                   OR title LIKE ? COLLATE NOCASE
                   OR first_user_message LIKE ? COLLATE NOCASE
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (pattern, pattern, pattern, limit),
            )
        else:
            column = field_map[field]
            cur.execute(
                f"""
                SELECT *
                FROM threads
                WHERE {column} LIKE ? COLLATE NOCASE
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (pattern, limit),
            )
        return [_row_to_thread(row) for row in cur.fetchall()]


def load_thread(db_path: str | Path, thread_id: str) -> ThreadRecord | None:
    with _connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM threads WHERE id = ?;", (thread_id,))
        row = cur.fetchone()
        return _row_to_thread(row) if row else None


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
                elif isinstance(item.get("content"), str) and item["content"].strip():
                    parts.append(item["content"])
        if parts:
            return "\n".join(parts).strip()
        return json.dumps(content, ensure_ascii=False, indent=2)
    if content is None:
        return ""
    return str(content)


def load_transcript(thread: ThreadRecord) -> Transcript:
    rollout_path = Path(thread.rollout_path)
    messages: list[MessageRecord] = []
    raw_event_count = 0
    message_count = 0

    try:
        with rollout_path.open("r", encoding="utf-8") as f:
            for index, line in enumerate(f, 1):
                raw_event_count += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("type") != "response_item":
                    continue

                payload = event.get("payload") or {}
                if payload.get("type") != "message":
                    continue

                message_count += 1
                messages.append(
                    MessageRecord(
                        index=message_count,
                        timestamp=str(event.get("timestamp", "")),
                        role=str(payload.get("role", "unknown")),
                        text=_extract_text(payload.get("content")),
                        raw_payload=payload,
                    )
                )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"找不到 rollout 文件：{rollout_path}") from exc
    except OSError as exc:
        raise OSError(f"读取 rollout 文件失败：{rollout_path}") from exc

    return Transcript(
        thread=thread,
        messages=messages,
        event_count=message_count,
        raw_event_count=raw_event_count,
    )
