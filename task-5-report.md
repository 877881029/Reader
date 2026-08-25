# Task 5 报告：Secure Explicit-Start WebEngine View

- 基线：`ee52167f879bd9e7d6fbb474af2079e086a58d9a`
- Task 5 主提交：`b0a3f988807a0e857119cb7da9c3639c1b9936fb`
- 范围：仅 Task 5；不接入 MainWindow 或真实 renderer 产品链路

## Important 修复结果

### 安全 fallback

- 在 `setHtml` 前断开 `loadFinished`、停止加载并停止计时器。
- 清空注入的 `QWebEngineScript`，解除 page WebChannel 与 bridge 注册，并关闭 JavaScript。
- fallback 使用空 `QUrl()`，不再以 PPTX 所在 file 目录作为 base URL。
- fallback HTML 超过保守的 Qt `setHtml` 安全字节上限时，改用固定安全文本，避免静默空白。

### Profile 与资源生命周期

- 每个 view 使用独立 off-the-record profile；profile parent 为 `QApplication`，page parent 为 profile。
- QApplication 持有的 `_WebEngineResources` 不依赖已删除 view；view `destroyed` 直接连接其 cleanup slot。
- 显式 `shutdown()` 与 `closeEvent()` 均执行安全清理；遗漏 shutdown 时也会解除 interceptor/channel 并最终释放 profile。
- teardown 顺序为：unset interceptor → deregister bridge → `page.setWebChannel(None)` → 换 inert page → unparent/deleteLater。

### 竞态与回调

- 删除 shutdown 中的 `runJavaScript(readerPptxDispose)`；不注册异步 Python callback。bundle 已通过 pagehide/beforeunload 处理 dispose，page 销毁会释放 JS context。
- `_load_finished(False)` 仅在已 start、尚未 ready、尚未 fallback、尚未 shutdown 时生效。
- qrc 缺失延期改为 view 子 `QTimer`；view 先删除时 timer 随 parent 销毁，不访问失效的 Python/C++ self。

### 安全不变量

- `_install_interceptor` helper 明确验证调用 `profile.setUrlRequestInterceptor`。
- 编码测试分别验证 `%23`、`%25`、Unicode UTF-8 编码，且无 `%2523` 双编码。
- allowlist 覆盖 `file/qrc/data/blob`；阻断覆盖 `http/https/ws/ftp/javascript`。
- 两个 view 的 profile 相互独立且均为 off-the-record。
- fallback 验证空 base、scripts 清空、channel 解绑、JavaScript 关闭。
- shutdown 验证 interceptor 解除、无 JavaScript 调用、顺序安全且幂等。

## 严格 TDD 证据

第一轮 RED：

```text
7 failed, 8 passed
```

失败分别命中 profile parent、fallback file base、超大 HTML、loadFinished 守卫、qrc timer 悬空回调、shutdown JavaScript 调用/顺序、closeEvent 清理。

补充顺序 RED：

```text
test_fallback_disconnects_load_signal_before_stopping FAILED
assert ['stop', 'disconnect'] == ['disconnect', 'stop']
```

GREEN：

```text
.venv\Scripts\python.exe -m pytest tests/test_pptx_view.py -v
16 passed in 6.43s
```

全量：

```text
.venv\Scripts\python.exe -m pytest -v
224 passed in 57.23s
```

IDE lint 无错误；`git diff --check` 通过。
