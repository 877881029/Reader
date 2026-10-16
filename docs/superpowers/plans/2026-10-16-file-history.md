# 计划：保存前保留历史版本（B3）

日期：2026-10-16
状态：已批准
规格：`docs/superpowers/specs/2026-10-16-file-history-design.md`

## 任务 1：历史存储
RED：`reader/history.py` 的 `FileHistory`（记录、去重、列出、上限与过期清理、大文件跳过、恢复）。GREEN：实现。

## 任务 2：保存时记录
RED：窗口保存覆盖时记录、首次保存不记录、另存为覆盖已有文件时记录。GREEN：`MainWindow` 接入可选 `history`，`ReaderApp` 提供默认实例。

## 任务 3：查看与恢复
RED：右键「历史版本」子菜单、只读版本标签、恢复写回并就地重新加载、有未保存修改时拒绝。GREEN：实现。

## 任务 4：文档与发布
功能全解、README、更新日志；`bump_version.py`（1.2.17 → 1.2.18）；发布门；安装；STATUS。
