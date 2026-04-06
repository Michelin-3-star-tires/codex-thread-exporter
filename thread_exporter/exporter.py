from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.8 及更早版本才会走到这里
    ZoneInfo = None  # type: ignore[assignment]

from .models import ExportOptions, MessageRecord, Transcript


EXPORT_VARIANT = "readable"

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


def _slugify(text: str, fallback: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return safe[:60] or fallback


def _choose_fence(text: str) -> str:
    longest_run = 0
    current_run = 0
    for char in text:
        if char == "`":
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0
    return "`" * max(3, longest_run + 1)


def _build_output_path(transcript: Transcript, output_dir: Path) -> Path:
    dt = datetime.fromtimestamp(transcript.thread.created_at, tz=timezone.utc).astimezone(BEIJING_TZ)
    date_folder = f"{dt:%Y%m%d}"
    thread_name = transcript.thread.title.strip() or transcript.thread.first_user_message.strip()
    if not thread_name:
        thread_name = transcript.thread.id
    file_name = (
        f"{dt:%H%M%S}_"
        f"{_slugify(thread_name, 'thread')}_"
        f"{_slugify(transcript.thread.id, 'thread')}.md"
    )
    return output_dir / date_folder / file_name


def render_markdown(transcript: Transcript, options: ExportOptions) -> str:
    timezone_mode = options.timezone_mode
    lines: list[str] = []

    lines.append(f"# {options.document_title.strip() or transcript.thread.title or transcript.thread.id}")
    lines.append("")

    if transcript.messages:
        for msg in transcript.messages:
            lines.extend(_render_message_block(msg, timezone_mode))
            lines.append("")
    else:
        lines.append("_未找到消息记录。_")

    if options.include_raw_events:
        lines.append("")
        lines.append("## 原始消息 JSON")
        for msg in transcript.messages:
            payload_text = json.dumps(msg.raw_payload, ensure_ascii=False, indent=2)
            fence = _choose_fence(payload_text)
            lines.append(
                f"### {msg.index}. {msg.role} | {_format_timestamp(msg.timestamp, timezone_mode)}"
            )
            lines.append(f"{fence}json")
            lines.append(payload_text)
            lines.append(fence)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_message_block(msg: MessageRecord, timezone_mode: str) -> list[str]:
    role_label, heading = _message_heading(msg.role)
    header = f"{heading} {role_label} · {msg.index} · {_format_timestamp(msg.timestamp, timezone_mode)}"
    body = msg.text or ""
    fence = _choose_fence(body)
    return [
        header,
        f"{fence}text",
        body,
        fence,
    ]


def _message_heading(role: str) -> tuple[str, str]:
    if role == "assistant":
        return "🟠 助手回复", "####"
    if role == "user":
        return "🔵 用户消息", "###"
    return f"◆ {role}消息", "####"


def export_transcript(transcript: Transcript, options: ExportOptions) -> Path:
    output_dir = Path(options.output_dir)
    path = _build_output_path(transcript, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(transcript, options), encoding="utf-8")
    return path
