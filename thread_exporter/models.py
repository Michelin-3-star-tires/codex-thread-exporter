from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ThreadRecord:
    id: str
    rollout_path: str
    created_at: int
    updated_at: int
    source: str
    model_provider: str
    cwd: str
    title: str
    sandbox_policy: str
    approval_mode: str
    tokens_used: int
    has_user_event: int
    archived: int
    archived_at: int | None
    git_sha: str | None
    git_branch: str | None
    git_origin_url: str | None
    cli_version: str
    first_user_message: str
    agent_nickname: str | None
    agent_role: str | None
    memory_mode: str
    model: str | None
    reasoning_effort: str | None
    agent_path: str | None


@dataclass(slots=True)
class MessageRecord:
    index: int
    timestamp: str
    role: str
    text: str
    raw_payload: dict[str, Any]


@dataclass(slots=True)
class Transcript:
    thread: ThreadRecord
    messages: list[MessageRecord]
    event_count: int
    raw_event_count: int


@dataclass(slots=True)
class ExportOptions:
    document_title: str
    timezone_mode: str
    metadata_profile: str
    include_raw_events: bool
    output_dir: str
