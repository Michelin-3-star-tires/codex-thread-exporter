from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.8 及更早版本才会走到这里
    ZoneInfo = None  # type: ignore[assignment]

from .models import ExportOptions, MessageRecord, Transcript


if ZoneInfo is None:
    BEIJING_TZ = timezone(timedelta(hours=8), name="UTC+08")
else:
    try:
        BEIJING_TZ = ZoneInfo("Asia/Shanghai")
    except Exception:  # pragma: no cover - 缺少 tzdata 时回退
        BEIJING_TZ = timezone(timedelta(hours=8), name="UTC+08")


def _resolve_timezone(mode: str) -> tzinfo:
    if mode == "utc":
        return timezone.utc
    return BEIJING_TZ


def _format_timestamp(ts: str, mode: str) -> str:
    if not ts:
        return ""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if mode == "dual":
        bj = dt.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        utc = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"{bj} / {utc}"
    tz = _resolve_timezone(mode)
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_epoch(ts: int | None, mode: str) -> str:
    if ts is None:
        return ""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    if mode == "dual":
        bj = dt.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
        utc = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"{bj} / {utc}"
    return dt.astimezone(_resolve_timezone(mode)).strftime("%Y-%m-%d %H:%M:%S %Z")


def _slugify(text: str, fallback: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return safe[:60] or fallback


def _build_output_path(transcript: Transcript, output_dir: Path) -> Path:
    dt = datetime.fromtimestamp(transcript.thread.updated_at, tz=timezone.utc).astimezone(BEIJING_TZ)
    date_parts = [f"{dt:%Y}", f"{dt:%m}", f"{dt:%d}"]
    thread_dir = _slugify(transcript.thread.id, "thread")
    title_slug = _slugify(transcript.thread.title, transcript.thread.id)
    file_name = f"{dt:%H%M%S}_{title_slug}.md"
    return output_dir.joinpath(*date_parts, thread_dir, file_name)


def _profile_fields(profile: str) -> list[tuple[str, str]]:
    if profile == "basic":
        return [
            ("线程ID", "id"),
            ("标题", "title"),
            ("来源", "source"),
            ("工作目录", "cwd"),
            ("创建时间", "created_at"),
            ("更新时间", "updated_at"),
            ("首条用户消息", "first_user_message"),
            ("导出文件", "rollout_path"),
        ]
    if profile == "runtime":
        return [
            ("线程ID", "id"),
            ("标题", "title"),
            ("来源", "source"),
            ("模型提供方", "model_provider"),
            ("模型", "model"),
            ("推理强度", "reasoning_effort"),
            ("CLI 版本", "cli_version"),
            ("审批模式", "approval_mode"),
            ("内存模式", "memory_mode"),
            ("tokens_used", "tokens_used"),
            ("sandbox_policy", "sandbox_policy"),
            ("archived", "archived"),
            ("archived_at", "archived_at"),
        ]
    return [
        ("线程ID", "id"),
        ("标题", "title"),
        ("来源", "source"),
        ("模型提供方", "model_provider"),
        ("模型", "model"),
        ("推理强度", "reasoning_effort"),
        ("工作目录", "cwd"),
        ("CLI 版本", "cli_version"),
        ("审批模式", "approval_mode"),
        ("内存模式", "memory_mode"),
        ("tokens_used", "tokens_used"),
        ("sandbox_policy", "sandbox_policy"),
        ("has_user_event", "has_user_event"),
        ("archived", "archived"),
        ("archived_at", "archived_at"),
        ("git_sha", "git_sha"),
        ("git_branch", "git_branch"),
        ("git_origin_url", "git_origin_url"),
        ("agent_nickname", "agent_nickname"),
        ("agent_role", "agent_role"),
        ("first_user_message", "first_user_message"),
        ("rollout_path", "rollout_path"),
        ("created_at", "created_at"),
        ("updated_at", "updated_at"),
    ]


def render_markdown(transcript: Transcript, options: ExportOptions) -> str:
    thread = transcript.thread
    timezone_mode = options.timezone_mode
    lines: list[str] = []

    lines.append(f"# 线程导出：{thread.title or thread.id}")
    lines.append("")
    lines.append("## 线程元信息")

    for label, field in _profile_fields(options.metadata_profile):
        value = getattr(thread, field)
        if field in {"created_at", "updated_at", "archived_at"}:
            value = _format_epoch(value, timezone_mode)
        elif value is None:
            value = ""
        elif field == "sandbox_policy":
            try:
                value = (
                    json.dumps(json.loads(value), ensure_ascii=False, indent=2)
                    if value
                    else ""
                )
            except json.JSONDecodeError:
                value = str(value)
        else:
            value = str(value)
        lines.append(f"- **{label}**：{value}")

    lines.append("")
    lines.append("## 对话消息")
    lines.append(f"- 消息数量：{len(transcript.messages)}")
    lines.append(f"- 原始事件数：{transcript.raw_event_count}")

    if transcript.messages:
        lines.append("")
        for msg in transcript.messages:
            lines.extend(_render_message_block(msg, timezone_mode))
            lines.append("")
    else:
        lines.append("")
        lines.append("_未找到消息记录。_")

    if options.include_raw_events:
        lines.append("")
        lines.append("## 原始消息 JSON")
        for msg in transcript.messages:
            lines.append(
                f"### {msg.index}. {msg.role} | {_format_timestamp(msg.timestamp, timezone_mode)}"
            )
            lines.append("<pre>")
            lines.append(
                html.escape(json.dumps(msg.raw_payload, ensure_ascii=False, indent=2))
            )
            lines.append("</pre>")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_message_block(msg: MessageRecord, timezone_mode: str) -> list[str]:
    header = f"### {msg.index}. {_format_timestamp(msg.timestamp, timezone_mode)} | {msg.role}"
    body = html.escape(msg.text or "")
    return [
        header,
        "<pre>",
        body,
        "</pre>",
    ]


def export_transcript(transcript: Transcript, options: ExportOptions) -> Path:
    output_dir = Path(options.output_dir)
    path = _build_output_path(transcript, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(transcript, options), encoding="utf-8")
    return path
