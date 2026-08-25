# PPTX Task 6 Report: Window Integration and Important Lifecycle Fixes

## 状态

完成。Task 6 主实现提交为 `184e58b`；本轮在其上修复两个 Important，严格执行 RED→GREEN。按用户指令创建新提交，不 amend、不 push、不修改 git config。

## Important 1：可管理的 visual 信号连接

根因：原 `_bind_visual_events` 每次 Office 失败恢复 visual 时追加三组匿名 lambda。generation guard 能阻止旧 handler 改状态，但旧 handler 入口仍会被逐次调用，连接数量随失败次数线性增长。

修复：

- `_Document` 保存 `visual_widget` 与 `visual_connections`（signal + callable）。
- `_bind_visual_events` 先调用 `_disconnect_visual_events`，再绑定当前 generation 的 ready、slide_changed、render_failed。
- `_restart_preview`、`_dispose_document_content` 与 rebind 都显式断开并清空旧连接。
- Office 失败仍保留同一 visual widget，但仅保留当前 generation 的三条连接。

验证：

- 连续三次 Office 失败后，document 中连接数仍为 3。
- 一次 ready/render_failed 仅进入当前 handler 一次。
- tab/window 销毁后连接记录为空，visual shutdown 仍只调用一次。

## Important 2：start 后二次生命周期校验

根因：`_install_document_content` 只在安装前校验。若 `content.start()` 同步关闭 tab/window，函数仍返回成功，调用方会继续写 artifact 并启动 Office availability probe，产生遗留临时目录和幽灵 worker。

修复：

- `start()` 返回后重新校验：
  - window 未 closing；
  - document 仍是 map 中同一对象；
  - generation 未变化；
  - layout 仍包含当前 content。
- 二次校验失败时断开当前 visual 连接；若 content 仍在 layout 中则移除并销毁，然后返回 `False`。
- 调用方收到 `False` 后恢复预安装的 mode/status/last_result/builtin_mode，并清理 worker output artifact；不会赋值 artifact，也不会 probe Office。

验证：

- `start()` 同步关闭 tab 与同步关闭 window 两条路径均覆盖。
- 临时 HTML artifact 被删除。
- Office availability 未调用，request/worker 容器为空。
- visual shutdown 恰好一次。

## 同步信号与 Office 状态补测

- visual 在 `start()` 内同步 emit ready 与 render_failed 时，绑定已生效：
  - slide count 正确；
  - status 为 `内置预览（视觉渲染失败）`；
  - `actionTextPreview` enabled；
  - `actionVisualPreview` disabled；
  - mode/builtin_mode 保持 visual。
- Office 失败继续保留当前 visual widget，status 精确为 `内置预览（Office 导出失败）`，builtin_mode 保持 visual。

## TDD 与验证记录

- RED：
  - `.venv\Scripts\python.exe -m pytest tests/test_window.py -k "repeated_office_failure or sync_signals or reentrancy_discards" -v`
  - `3 failed, 1 passed, 1 error`。
  - 产品失败符合预期：缺少 `visual_connections`，同步 close 后仍调用 Office availability；window 参数用例的 pytest-qt teardown 随后修正为不注册已自删除窗口。
- GREEN 聚焦：
  - 同命令：`4 passed, 79 deselected`。
- 完整窗口：
  - `.venv\Scripts\python.exe -m pytest tests/test_window.py -v`
  - `83 passed`。
- Python 全量：
  - `.venv\Scripts\python.exe -m pytest -v`
  - `240 passed`。
- 静态检查：
  - IDE lint：无错误。
  - `git diff --check`：通过。

## 回归核对

- [x] repeated Office failure 不堆积 signal handlers
- [x] stale generation 不进入旧 handler
- [x] start 同步信号在 bind-after/start-before 顺序下生效
- [x] start 同步 close 不写 artifact、不 probe Office
- [x] tab/window close 均 shutdown once
- [x] shared executor 路由测试保持通过
- [x] PDF pin/cleanup 测试保持通过
- [x] late result/late signal 测试保持通过
- [x] Office failure 保 widget、精确状态与 visual builtin_mode

## 提交策略

新建独立提交；不 amend、不 push、不修改 git config。
