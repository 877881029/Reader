# Task 5 报告：Secure Explicit-Start WebEngine View

## 状态

已完成。基线：`ee52167f879bd9e7d6fbb474af2079e086a58d9a`。

## 交付

- 新增 `src/reader/preview/pptx_view.py`
  - `PptxVisualView` 构造阶段不加载；`start()` 仅执行一次并启动 15 秒超时。
  - 独立 off-the-record `QWebEngineProfile` / `QWebEnginePage`。
  - 允许本地内容访问 file URL，禁止访问 remote URL。
  - `OfflineRequestInterceptor` 仅放行 `file/qrc/data/blob`，以锁保护 blocked URL 快照，不从 Chromium 请求线程发 Qt Signal。
  - 显式导入 `PySide6.QtWebChannel` 注册 qrc，并在 `DocumentCreation`、`MainWorld` 注入 `qwebchannel.js`。
  - `PptxBridge` 提供 `sourceUrl` / `testFailSlide` 常量属性，以及 ready/error/slide slots 与 signals。
  - `sourceUrl` 由 `QUrl.fromLocalFile(...).toString(FullyEncoded)` 生成一次，不进入 viewer query。
  - bundle 加载失败、超时、bridge error、WebChannel 资源缺失统一幂等切换安全 fallback HTML，并仅发一次 `render_failed`。
  - `ready` 与 `slide_changed` 对外转发；ready 后已排队的超时回调被忽略。
  - `shutdown()` 最佳努力调用 `readerPptxDispose()`，按所有权顺序解绑 interceptor/channel/page/profile，并保持幂等。
- 新增 `tests/test_pptx_view.py`，覆盖显式启动、隔离设置、脚本注入、单次 URL 编码、fallback 收敛、ready/slide relay、超时竞态、离线 allowlist 与 teardown。
- 更新 `docs/STATUS.md`，下一步为 Task 6 窗口集成。

## TDD 证据

RED：

```text
test_queued_startup_timeout_after_ready_is_ignored FAILED
AssertionError: assert ['viewer startup timed out'] == []
```

该测试证明 ready 与已排队 timeout 的竞态会错误切换 fallback。增加 `_startup_complete` 守卫后转绿。

## 验证

- 聚焦：`.venv\Scripts\python.exe -m pytest tests/test_pptx_view.py -v`
  - `9 passed in 3.91s`
- 全量：`.venv\Scripts\python.exe -m pytest -v`
  - `217 passed in 56.53s`
- IDE lint：无错误。

## 范围

按要求未把真实 renderer 接入 `MainWindow`；窗口安装、模式切换与完整产品生命周期属于 Task 6，真实 WebEngine fidelity/offline 集成验证属于 Task 7。
