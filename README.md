# 线程查询导出器

这是一个用于查询 `C:\Users\86274\.codex\state_5.sqlite` 中 Codex 线程记录，并将选中的线程导出为 Markdown 的小工具。

## 项目简介

- 支持按线程 ID 前缀、标题前缀、首条用户消息前缀进行检索
- 支持在多个匹配结果里选择一个或全部导出
- 导出的 Markdown 会包含线程元信息、消息时间戳和消息正文
- 适合把某个完整对话整理成可阅读、可归档的文档

## 环境要求

- Python 3.13 或更高版本
- `uv`
- 本地可访问目标 SQLite 文件

## 安装步骤

1. 进入项目目录
2. 如果需要测试，执行 `uv add --dev pytest`
3. 同步环境：`uv sync`

## 运行方式

交互式运行：

```powershell
uv run python run.py
```

或者：

```powershell
uv run python -m thread_exporter
```

导出结果默认保存在 `output/YYYY/MM/DD/thread_id/` 目录下。

## 建议的导出参数

- 时间格式：北京时间
- 元信息：基础信息 + 运行信息
- 消息范围：仅导出消息正文
- 文件名：`更新时间_线程ID.md`
