from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import shorten

from .db import load_transcript, search_threads
from .exporter import export_transcript
from .models import ExportOptions


DEFAULT_DB = r"C:\Users\86274\.codex\state_5.sqlite"
DEFAULT_OUTPUT = "output"


def _prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def _prompt_choice(text: str, choices: dict[str, str], default: str) -> str:
    print(text)
    for key, label in choices.items():
        mark = "（默认）" if key == default and "默认" not in label else ""
        print(f"  {key}. {label}{mark}")
    while True:
        value = input(f"请选择 [直接回车默认 {default}]: ").strip() or default
        if value in choices:
            return value
        print("输入无效，请重新选择。")


def _prompt_yes_no(text: str, default: bool = False) -> bool:
    default_label = "y" if default else "n"
    value = input(f"{text} [y/n，默认 {default_label}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "是", "1"}


def _show_matches(matches) -> None:
    print("\n匹配结果：")
    for i, thread in enumerate(matches, 1):
        preview = shorten(
            thread.first_user_message.replace("\n", " "), width=56, placeholder="..."
        )
        title = shorten(thread.title.replace("\n", " "), width=56, placeholder="...")
        updated = (
            datetime.fromtimestamp(thread.updated_at, tz=timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        print(f"  {i}. id={thread.id}")
        print(f"     更新：{updated}")
        print(f"     标题：{title}")
        print(f"     首句：{preview}")
        print()


def _parse_selection(raw: str, total: int) -> list[int]:
    if raw.strip().lower() in {"0", "all", "a", "全部"}:
        return list(range(1, total + 1))
    indexes: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        index = int(part)
        if index < 1 or index > total:
            raise ValueError(f"索引超出范围：{index}")
        if index not in indexes:
            indexes.append(index)
    return indexes


def main() -> None:
    print("Codex对话查询导出工具")
    db_path = DEFAULT_DB
    if not Path(db_path).exists():
        db_path = _prompt("默认路径不存在，请手动输入 SQLite 路径")

    field = _prompt_choice(
        "请选择查找方式",
        {
            "1": "按首句原文找（默认）",
            "2": "按标题摘要找",
            "3": "综合查找",
            "4": "按 thread id 找",
        },
        "1",
    )
    field_map = {"1": "first_user_message", "2": "title", "3": "all", "4": "id"}
    keyword_prompt_map = {
        "1": "请输入首句原文开头",
        "2": "请输入标题开头",
        "3": "请输入要综合匹配的前缀",
        "4": "请输入 thread id 前缀",
    }
    keyword = _prompt(keyword_prompt_map[field])
    if not keyword:
        print("未输入查找内容，已退出。")
        return

    matches = search_threads(db_path, keyword, field_map[field], limit=20)
    if not matches:
        print("没有找到匹配的线程。")
        return

    _show_matches(matches)
    selection = _prompt("请输入序号（支持逗号分隔；0=全部；回车默认 1）", "1")
    try:
        indexes = _parse_selection(selection, len(matches))
    except ValueError as exc:
        print(f"选择失败：{exc}")
        return

    metadata_profile = "all"
    print("元信息级别：全部信息（推荐，默认）")

    include_raw_events = False
    print("是否附带原始消息 JSON：n（默认）")
    print(f"导出目录：{DEFAULT_OUTPUT}（默认）")
    output_dir = DEFAULT_OUTPUT

    selected = [matches[i - 1] for i in indexes]
    print(f"\n准备导出 {len(selected)} 个线程。")
    for thread in selected:
        try:
            transcript = load_transcript(thread)
            path = export_transcript(
                transcript,
                ExportOptions(
                    document_title=keyword,
                    timezone_mode="beijing",
                    metadata_profile=metadata_profile,
                    include_raw_events=include_raw_events,
                    output_dir=output_dir,
                ),
            )
            print(f"已导出：{path}")
        except Exception as exc:
            print(f"导出失败：{thread.id} -> {exc}")
