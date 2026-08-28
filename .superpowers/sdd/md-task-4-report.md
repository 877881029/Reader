# Markdown Visual Preview Task 4 Report

## RED
- 新增行为测试：
  - `tests/test_formats_md.py::test_markdown_visual_contract_and_safe_fallback`
  - `tests/test_pipeline.py::test_markdown_default_is_visual_and_never_calls_office`
  - `tests/test_pipeline.py::test_markdown_visual_mode_supported_and_never_calls_office`
  - `tests/test_pipeline.py::test_visual_mode_rejects_non_visual_suffix`
  - `tests/test_cache.py::test_put_rejects_markdown_visual_kind`
  - `tests/test_window.py::test_markdown_visual_skips_cache_get_and_put`
- RED 执行：`python -m pytest tests/test_formats_md.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py -v`
- RED 结果：`5 failed, 121 passed`，失败点与预期一致（缺少 `md.to_visual`、`markdown` kind、`.md` visual 路由与 worker cache skip）。

## GREEN
- `src/reader/preview/result.py`：`PreviewKind` 增加 `"markdown"`。
- `src/reader/formats/md.py`：
  - `MarkdownIt("commonmark", {"html": False}).enable("table")`
  - `_read(..., errors="replace")` 支持 invalid UTF-8 replacement
  - 新增 `to_visual()`，返回 `kind="markdown"`、`html=""`、安全 `fallback_html`
- `src/reader/preview/pipeline.py`：
  - `visual` 仅允许 `.pptx/.md`
  - `.md` 在 `builtin/visual` 统一走 `fmt_md.to_visual`
  - Markdown 保持不触发 Office
- `src/reader/shell/window.py`（`_PreviewWorker.run`）：
  - `visual_suffix = suffix in {".pptx", ".md"}`
  - visual strategy 继续跳过 cache `get/put`
- 回归对齐：
  - `tests/test_pipeline.py` 旧 markdown builtin 断言迁移到 visual 契约
  - `tests/test_window.py::test_cache_hit_skips_preview_and_cache_miss_puts` 改用 `.docx`，避免被新的 markdown visual 默认行为影响
  - `tests/test_real_fixtures.py` markdown 实测断言更新为 visual 契约（`html==""` + `fallback_html`）

## Verification
- 聚焦 GREEN：`python -m pytest tests/test_formats_md.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py -v` -> `126 passed`
- 全量 Python：`python -m pytest -v` -> `275 passed, 1 skipped`

## Concerns
- 无新增 blocker；本任务未接入 `MarkdownVisualView/MainWindow` factory（按 Task 5/6 边界保留）。
- Closed: controller 已用 owner helper 成功 push `2929a6f`，`main` 与 `origin/main` 已同步，Task 4 同步阻塞解除。
