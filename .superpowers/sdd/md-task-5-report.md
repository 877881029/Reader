# Markdown Visual Preview Task 5 Report

## RED
- 新增 `tests/test_md_view.py`，覆盖：
  - `resolve_wikilink()` 同目录解析与输入边界（裸名、`.md`、空值、绝对路径、分隔符、`..`、非 md 后缀、缺失文件、symlink escape）。
  - `MarkdownBridge` 契约（`sourceUrl` property、`wikiExists/openWiki/viewerReady/viewerError` slot、`open_path` canonical、`missing` 256 字符上限）。
  - `OfflineRequestInterceptor` allowlist（source 目录 descendants、bundle descendants、`qrc/data/blob`）与 remote/escape 阻断。
  - `MarkdownVisualView` 生命周期（构造不加载、`start()` 单次加载、off-the-record profile、fallback 原子 detach、oversize fallback cap、shutdown 幂等、close-during-start、delete cleanup）。
- RED 执行：`python -m pytest tests/test_md_view.py -v`
- RED 结果：`ModuleNotFoundError: No module named 'reader.preview.md_view'`（符合预期）。

## GREEN
- 新增 `src/reader/preview/md_view.py`：
  - `resolve_wikilink(source, target)`：仅允许同目录 `.md`/裸名，返回 canonical resolved path。
  - `MarkdownBridge`：`sourceUrl` constant property；`wikiExists` 返回 bool；`openWiki` 成功仅 emit canonical path，失败 emit bounded missing；shutdown 后 late call no-op。
  - `OfflineRequestInterceptor`：Windows `normcase(realpath)` canonical 化，允许 source 目录与 bundle 目录 descendants，阻断 sibling-parent/symlink escape 与 remote。
  - `MarkdownVisualView`：隔离 profile/page/channel/interceptor 资源所有权；显式 `start()`；`ready` 仅 emit `1`；fallback 前原子 stop + detach scripts/channel/interceptor + disable JS；`setHtml(..., QUrl())`；1.9MB fallback cap。
- 新增并转绿 `tests/test_md_view.py` 全部 16 项。

## Verification
- Task5：`python -m pytest tests/test_md_view.py -v` -> `16 passed`
- PPTX 回归：`python -m pytest tests/test_pptx_view.py -v` -> `17 passed`
- Python 全量：`python -m pytest -v` -> `291 passed, 1 skipped`

## Concerns
- 本任务严格限定在 `md_view.py` 与其测试，未改 `PptxVisualView`/公共抽象，保持 Task5 边界。
- MainWindow 集成（`kind="markdown"` 默认 viewer factory、wiki-link 开新标签）保留到 Task 6。
- 同步状态已关闭：controller 已使用 owner credential 成功推送 `08f5ef8`（包含 Task 5 提交 `89cbc7a`），当前 `main` 与 `origin/main` 已同步。

## Reviewer Request Changes (2026-08-28)

### RED
- 先补失败用例并复现：
  - `test_resolve_wikilink_uses_lexical_parent_when_source_resolve_points_elsewhere`
  - `test_interceptor_uses_lexical_root_when_source_resolve_points_elsewhere`
  - `test_fallback_keeps_interceptor_until_shutdown`
- RED 执行：`python -m pytest tests/test_md_view.py -v`
- RED 结果：`3 failed, 20 passed`，失败点与评审意见一致（source symlink lexical root、fallback 过早卸载 interceptor）。

### GREEN
- `src/reader/preview/md_view.py`：
  - 新增 `_absolute_lexical_path()`；`MarkdownBridge.sourceUrl` 与 resolver/interceptor 均改为 lexical absolute source root。
  - `resolve_wikilink()` 改为 lexical parent 解析，再以 canonical 路径做同目录约束，保持 symlink escape 拒绝。
  - `OfflineRequestInterceptor` allowlist 改为：exact canonical source target + canonical lexical-root descendants + canonical bundle descendants。
  - `_show_fallback()` 改为保留 interceptor（`detach_interceptor=False`），仅在 `shutdown()` detach。
- `tests/test_md_view.py`：
  - 补充 reviewer 指定 minor 覆盖：source target sibling 阻断、`qrc/data/blob` allow、prefix collision 阻断。

### Verification
- Task5：`python -m pytest tests/test_md_view.py -v` -> `23 passed`
- PPTX 回归：`python -m pytest tests/test_pptx_view.py -v` -> `17 passed`
- Python 全量：`python -m pytest -v` -> `298 passed, 1 skipped`
- Push：controller 已成功推送 `ac8d6a2`（包含 reviewer 修复提交 `408440b`），`main` 与 `origin/main` 已同步。
