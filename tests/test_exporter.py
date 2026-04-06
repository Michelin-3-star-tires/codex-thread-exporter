from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from thread_exporter.db import load_thread, load_transcript, search_threads
from thread_exporter.exporter import export_transcript, render_markdown
from thread_exporter.models import ExportOptions


def _build_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "state.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            rollout_path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            source TEXT NOT NULL,
            model_provider TEXT NOT NULL,
            cwd TEXT NOT NULL,
            title TEXT NOT NULL,
            sandbox_policy TEXT NOT NULL,
            approval_mode TEXT NOT NULL,
            tokens_used INTEGER NOT NULL,
            has_user_event INTEGER NOT NULL,
            archived INTEGER NOT NULL,
            archived_at INTEGER,
            git_sha TEXT,
            git_branch TEXT,
            git_origin_url TEXT,
            cli_version TEXT NOT NULL,
            first_user_message TEXT NOT NULL,
            agent_nickname TEXT,
            agent_role TEXT,
            memory_mode TEXT NOT NULL,
            model TEXT,
            reasoning_effort TEXT,
            agent_path TEXT
        )
        """
    )
    rollout_path = tmp_path / "rollout.jsonl"
    rollout_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-04-01T09:48:49.535Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "你好"}],
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "timestamp": "2026-04-01T09:49:35.609Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "收到"}],
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )
    conn.execute(
        """
        INSERT INTO threads VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            "thread-001",
            str(rollout_path),
            1775009031,
            1775010179,
            "vscode",
            "openai",
            r"D:\test_project",
            "测试线程",
            "{}",
            "never",
            10,
            1,
            0,
            None,
            None,
            None,
            None,
            "0.118.0-alpha.2",
            "你好",
            None,
            None,
            "enabled",
            "gpt-5.4",
            "xhigh",
            None,
        ),
    )
    conn.commit()
    conn.close()
    return db_path


def test_search_and_load(tmp_path: Path) -> None:
    db_path = _build_db(tmp_path)
    matches = search_threads(db_path, "你", "first_user_message")
    assert len(matches) == 1
    thread = load_thread(db_path, "thread-001")
    assert thread is not None
    transcript = load_transcript(thread)
    assert len(transcript.messages) == 2
    assert transcript.messages[0].text == "你好"


def test_render_and_export(tmp_path: Path) -> None:
    db_path = _build_db(tmp_path)
    thread = load_thread(db_path, "thread-001")
    assert thread is not None
    transcript = load_transcript(thread)
    markdown = render_markdown(
        transcript,
        ExportOptions(
            timezone_mode="beijing",
            metadata_profile="basic",
            include_raw_events=False,
            output_dir=str(tmp_path / "output"),
        ),
    )
    assert "线程元信息" in markdown
    assert "测试线程" in markdown
    path = export_transcript(
        transcript,
        ExportOptions(
            timezone_mode="beijing",
            metadata_profile="basic",
            include_raw_events=False,
            output_dir=str(tmp_path / "output"),
        ),
    )
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("# 线程导出")
