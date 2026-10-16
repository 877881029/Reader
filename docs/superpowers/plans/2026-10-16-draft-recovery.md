# 计划：未保存内容自动暂存与恢复（B1）

日期：2026-10-16
状态：已批准
规格：`docs/superpowers/specs/2026-10-16-draft-recovery-design.md`

## 任务 1：暂存存储
RED：`reader/drafts.py` 的 `DraftStore` 写入/读取/删除/损坏跳过。GREEN：实现，原子写。

## 任务 2：视图快照与恢复
RED：`CodeTextView` / `MarkdownTextView` 的 `draft_snapshot()` 与 `restore_draft()`。GREEN：实现。

## 任务 3：窗口暂存
RED：编辑后防抖写入、干净后删除、关闭标签删除、失去焦点立即写、移动标签后仍暂存。GREEN：`MainWindow` 接入可选的暂存对象。

## 任务 4：启动恢复与会话结束
RED：启动时恢复到第一个窗口并提示；会话结束写入全部暂存且不弹询问。GREEN：`ReaderApp` 与 `__main__`。

## 任务 5：文档、发布
README / 功能全解；升版本 0.1.2；发布门；安装；STATUS。
