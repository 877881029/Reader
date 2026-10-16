# 计划：重新打开刚关闭的标签（B2）

日期：2026-10-16
状态：已实施（2026-10-16，1.2.17）
规格：`docs/superpowers/specs/2026-10-16-reopen-closed-tab-design.md`

## 任务 1：最近关闭列表
RED：`reader/shell/closed_tabs.py` 的 `ClosedTabs`（后进先出、去重、上限、跳过缺失）。GREEN：实现。

## 任务 2：窗口与应用接入
RED：关闭后 `Ctrl+Shift+T` 重新打开、未命名不记录、空列表提示、窗口关闭后跨窗口找回、已打开则切过去、右键菜单项。GREEN：`MainWindow` 动作与记录，`ReaderApp` 共享列表并负责跨窗口聚焦。

## 任务 3：文档与发布
README 快捷键表、功能全解、更新日志；`bump_version.py --set 1.2.17`；发布门；安装；STATUS。
