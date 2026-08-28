# Markdown Visual Preview Task 7 Report

日期：2026-08-28

## 范围

- 真实 Chromium fidelity（heading/table/python/mermaid/image/wikilink）
- Mermaid 隔离（1 valid SVG + 1 invalid error）
- relative image/wiki 行为
- 网络阻断（HTTP/HTTPS/WS/WSS）与 shutdown/profile cleanup

## TDD 证据

### RED 1（真实 QWebEngine）

命令：

```bash
python -m pytest tests/test_md_webengine.py -v
```

结果：`1 failed, 1 passed`

- 失败点：`test_real_view_renders_markdown_mermaid_image_and_wikilink_states`
- 现象：点击 missing wiki 后 `missing_link` 未触发（`qtbot.waitUntil` 超时）

### RED 2（最小归属 web 单元回归）

命令：

```bash
npm test -- src/viewer.test.ts
```

结果：`2 failed, 5 passed`

- 失败点均为 missing wiki click 未透传 `openWiki("missing")`

### GREEN（最小修复后）

修复：

- `web/md-viewer/src/viewer.ts`
- wiki click 处理从“仅 resolved 才调用 `openWiki`”改为“active 即透传 `openWiki`”，由 bridge 统一决定 resolved/missing 信号

验证：

- `npm test -- src/viewer.test.ts` -> `7 passed`
- `python -m pytest tests/test_md_webengine.py -v` -> `2 passed`

## 交付内容

- 新增：`tests/fixtures/md/visual-document.md`
- 新增：`tests/fixtures/md/linked-note.md`
- 新增：`tests/fixtures/md/diagram.png`
- 新增：`tests/test_md_webengine.py`
- 修改：`web/md-viewer/src/viewer.ts`
- 修改：`web/md-viewer/src/viewer.test.ts`
- 重建：`assets/md-viewer/*`

## 关键断言覆盖

- DOM：
  - `title == "文档地图"`
  - `table_rows >= 2`
  - `python_code is True`
  - `mermaid_svg == 1`
  - `mermaid_errors == 1`
  - `raw_valid_source_visible is False`
  - `local_image_loaded is True`
  - `resolved_class is True`
  - `missing_class is True`
- 信号：
  - resolved wiki click -> `open_path == canonical linked-note.md`
  - missing wiki click -> only `missing_link == "missing-note"`
- 网络：
  - 注入前 `blocked_urls()==()`
  - 临时打开 LocalContentCanAccessRemoteUrls 后注入 HTTP/HTTPS/WS/WSS
  - 拦截器记录与阻断精确四项
- 生命周期：
  - 真实 WebEngine 用例均在 `finally` 中 `shutdown()`
  - `qtbot.waitUntil(not shiboken6.isValid(profile))` 验证 profile 释放

## 回归矩阵

- `npm test` -> `21 passed`
- `python -m pytest tests/test_md_view.py -v` -> `23 passed`
- `python -m pytest tests/test_pptx_webengine.py -v` -> `3 passed`
- `python -m pytest -v` -> `306 passed, 1 skipped`

## 同步状态

- controller 已成功 owner push `HEAD`（`4b74767`），Task 7 同步阻塞已关闭。
