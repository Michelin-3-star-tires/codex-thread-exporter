# Codex 对话查询导出工具

> English: Query local Codex thread records and export selected conversations to Markdown.

这是一个用于查询本地 Codex 线程数据库，并将选中的线程导出为 Markdown 的工具。

## 项目简介

- 支持按线程 ID、标题、首条用户消息前缀进行检索
- 支持在多个匹配结果里选择单个导出或全部导出
- 导出的 Markdown 默认只保留对话正文
- 适合把完整对话整理成可阅读、可归档的文档

## 环境要求

- Python 3.13 或更高版本
- `uv`
- 本地可访问目标 SQLite 文件

## 安装

1. 克隆仓库
2. 执行 `uv sync`

## 运行

1. 执行 `uv run pytest` 确认环境正常
2. 按需启动 `uv run thread-exporter`

## 运行方式

交互式运行：

```powershell
uv run python run.py
```

或者直接使用命令：

```powershell
uv run thread-exporter
```

如需显式指定数据库路径和导出目录：

```powershell
uv run thread-exporter --db-path "D:\path\to\state_5.sqlite" --output-dir output
```

## 配置说明

程序会按以下顺序寻找数据库：

1. 命令行参数 `--db-path`
2. 环境变量 `CODEX_STATE_DB`
3. `~/.codex/state_5.sqlite`

如果以上路径都不可用，程序会提示你手动输入路径。

## 导出结果

- 默认输出目录为 `output/`
- 按日期分层保存到 `output/YYYYMMDD/`
- 文件名格式为 `创建时间_标题或首句_slug_线程ID.md`
- 默认导出阅读版，仅保留对话正文

## 项目结构

- `thread_exporter/cli.py`：交互式流程与命令行入口
- `thread_exporter/db.py`：SQLite 读取和线程解析
- `thread_exporter/exporter.py`：Markdown 生成与落盘
- `tests/`：核心逻辑测试
- `CONTRIBUTING.md`：贡献流程、测试命令和提交规范
- `CODE_OF_CONDUCT.md`：社区行为准则
- `RELEASE_NOTES.md`：版本发布说明
- `.github/`：CI、Issue 模板和 PR 模板

## 贡献

欢迎提交 Issue 和 Pull Request。开始贡献前，建议先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 社区准则

参与协作前，请先阅读 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

## 许可证

本项目使用 MIT 许可证，详见 [`LICENSE`](LICENSE)。
