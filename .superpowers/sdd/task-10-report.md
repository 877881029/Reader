# Reader v1 Task 10 实施报告

## 状态

已在基线 `2e298cfe3390c0a5582ed3d1449df49d819aef32`、分支 `main` 上完成 MainWindow 标签页、后台预览、缓存、新窗口、拖放和 Task 9 IPC 协同。

## 实现摘要

- `MainWindow.open_paths()` 只做打开决策、立即创建“正在加载…”标签并投递 `QRunnable`；预览解析、Office COM 路径和 `PreviewCache.get/put` 均在 `QThreadPool` 工作线程执行。
- 工作线程通过 Qt signal 返回 `PreviewResult` 或异常；QWebEngineView/QLabel 只在 GUI 线程创建和装入。
- 每个文档使用 UUID document id 映射到稳定 page widget。关闭加载中的标签会删除映射，迟到结果被忽略，不依赖可变化的 tab index。
- 后台流程按 `cache.get(path, "auto") -> preview(...) -> cache.put(...)` 执行；缓存构造、读取或写入异常均不阻断实际预览。
- unsupported 文件不创建标签，以状态栏“无法打开”通知；单个预览错误只替换对应标签内容。
- 同路径在当前窗口聚焦；最后标签关闭后保留空窗口；支持多文件拖放和 `actionNewWindow`。
- 默认 viewer 每次需要时优先导入并创建 `QWebEngineView`；测试通过 viewer factory 注入 QLabel，没有形成永久产品降级状态。
- `ReaderApp` 只创建并持有一个 `SingleInstance`，所有新窗口复用该 IPC owner，关闭时由 ReaderApp 统一清理。
- `set_app_user_model_id()` 在非 Windows 环境安全 no-op，在 Windows 使用默认值 `Reader.Desktop`。
- 测试会话在收集阶段统一创建 `QApplication`，避免既有 IPC 测试先创建 `QCoreApplication` 后无法运行 QWidget 测试。

## TDD 证据

### RED

先创建 `tests/test_window.py`，然后运行：

```text
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_window.py -v
```

结果：`11 failed, 2 errors`。失败原因均为预期的 `reader.app` / `reader.shell` 尚不存在。

### GREEN

完成最小实现后运行同一命令：

```text
13 passed in 3.00s
```

首次全量运行在首个 QWidget 测试处以 Windows 原生退出码 `-1073740791` 终止。定位为 `tests/test_ipc.py` 收集阶段先创建 `QCoreApplication`，随后无法升级为 `QApplication`。在 `tests/conftest.py` 统一预创建 `QApplication` 后，全量通过。

## 线程证据

`test_open_paths_returns_while_preview_worker_is_blocked` 使用阻塞 Event 的 fake preview：

- `open_paths()` 在 worker 仍阻塞时立即返回；
- 返回时 loading tab 已存在并显示“正在加载…”；
- fake preview 记录的 thread id 与 GUI/测试线程 id 不同；
- 释放 worker 后，Qt signal 驱动 GUI 线程换入 viewer 并更新状态栏。

测试还覆盖缓存 hit 跳过 preview、miss 后 put、缓存异常继续预览，以及关闭 loading tab 后迟到结果不会覆盖已移位标签。

## 验证

- 定向：`13 passed in 3.00s`
- 全量：`76 passed in 6.58s`
- IDE lint：改动文件无诊断
- `git diff --check`：无空白错误

## 自审

逐项核对了用户八条优先规格和 brief 接口。后台任务没有创建 QWidget；GUI 回调按 document id 查找 page；unsupported 路径无 QMessageBox；ReaderApp 的 IPC server 初始化不随窗口数增加。

## 顾虑

- 自动测试按授权使用注入的 QLabel viewer，没有在 offscreen 环境实例化 Chromium；产品默认路径仍是 QWebEngineView。
- Office COM 的真实应用联调依赖本机 Office，当前由既有 Office backend 单元测试和后台 fake preview 线程测试覆盖，未执行真实 Office 自动化。

---

## 审查修复追加记录（2026-08-21）

### 修复范围

- 新增 GUI-affine `PreviewExecutor` owner。`_WorkerSignals` 在 GUI 线程创建并以 executor 为 parent；worker `setAutoDelete(False)`，由 executor registry 强引用。
- worker completion 到 executor、executor 到 MainWindow 均显式使用 `Qt.QueuedConnection`。executor 在 GUI slot 中移除 registry、`deleteLater()` signals 并释放 worker 最后一个 Python 强引用。
- 独立 MainWindow 创建专用 `QThreadPool(maxThreadCount=1)`；ReaderApp 创建一个 executor 并由所有窗口共享，串行化 PreviewCache 和 Office COM 工作。
- executor 保管尚未被 GUI 消费的 completion。关闭 tab/窗口会 cancel active 或 pending job；worker 迟到时只清理结果，不创建 widget。
- viewer factory 接口调整为 `(PreviewResult, source_path)`。默认 HTML viewer 使用 `asset_dir` 目录 URL；没有 `asset_dir` 时使用源文件 parent 目录 URL。
- 所有 PDF 在 worker 内复制到 `reader-document-*` 私有目录，再向 GUI 发布。缓存 slot 删除后标签副本仍存在；关闭 tab、窗口、reentrant viewer 丢弃和取消路径都会清理私有目录。
- Office PDF result 现在用 `asset_dir` 标记 export temp dir。pin 成功后只在原 PDF 确实位于该目录下时消费该目录，避免删除任意外部路径。
- viewer factory 返回后再次按 document id/page identity 检查；标签已关闭时 `deleteLater()` 新 widget 并清理 artifact，不再 assert page layout 存活。
- 最后窗口 `destroyed` 后 ReaderApp 移除窗口并关闭 IPC；`close_all()` 不再预先清空窗口列表。`is_primary_instance()` 暴露 `become_server()` 结果。
- 低成本修复包括 error-kind QLabel、空 tab title 断言，以及用 executor completion 条件替代固定 sleep。

### 审查修复 TDD：RED

先扩展 `tests/test_window.py` 和 `tests/test_office.py`，随后运行：

```text
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_window.py tests/test_office.py -v
```

结果为 `9 failed, 19 passed, 2 errors`。预期失败明确暴露：

- MainWindow 没有可靠 executor/worker registry；
- ReaderApp 无 primary 状态且最后窗口销毁不释放 IPC；
- viewer 无 source/baseUrl 接口；
- PDF 未 pin，cache 原文件仍直接交给 viewer；
- reentrant close 和窗口关闭迟到 completion 无安全清理；
- Office PDF 未标记 export `asset_dir`。

### 审查修复 TDD：GREEN

实现 owner/registry、串行 executor、artifact pin 和窗口生命周期后：

```text
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_window.py tests/test_office.py -v
29 passed in 6.44s
```

继续补强 Office 临时目录消费、pin 失败清理、已加载 PDF 的窗口关闭清理、真实 `SingleInstance`/`QLockFile` 释放测试后，最终窗口定向测试为 `23 passed in 7.43s`；真实单实例锁释放测试单独运行 `1 passed in 2.65s`。

### 线程与析构证据

`test_open_paths_returns_while_preview_worker_is_blocked` 在 worker 阻塞期间执行 `gc.collect()`，registry 仍持有 worker；completion 后等待 registry/pending 清零，再执行 `gc.collect()`。viewer factory 记录 `QThread.currentThread()`，断言与 MainWindow GUI thread 相同。

worker 自身不创建任何 QWidget。窗口关闭测试在 worker 仍阻塞时关闭 MainWindow，随后释放 worker，并以 executor `active_count()==0` 为确定完成条件；viewer 调用次数保持零。

### PDF 生命周期证据

- cache hit PDF 会先复制到私有目录；删除 cache slot 原 PDF 后，viewer 使用的 copy 仍存在。
- close tab 后等待并确认私有 PDF 被删除。
- Office-owned export 目录在 pin 成功后被消费，私有 copy 保留。
- PDF pin 复制失败时也会清理已确认归属 Office 的 export 目录；该边界测试先 RED 后 GREEN。
- viewer factory 内 reentrant close tab 后，返回的 orphan widget 被 `deleteLater()`，私有 artifact 被清理。

### IPC 生命周期证据

- fake IPC 使用排他 owner 状态验证：首个 ReaderApp 最后窗口销毁并释放 server 后，第二个 ReaderApp 才能成为 primary。
- 真实 `SingleInstance` 使用唯一 server name 和独立 lock dir 验证：最后窗口销毁后，后续 ReaderApp 能重新获得 `QLocalServer` 和 `QLockFile`。

### 审查修复验证

- `tests/test_window.py`：23 passed
- `tests/test_office.py tests/test_ipc.py tests/test_cache.py`：32 passed
- 首轮全量（补真实锁测试前）：83 passed in 9.94s
- 最终全量：87 passed in 10.78s
- IDE lint：相关改动文件无诊断
- `git diff --check`：无空白错误

### 全量验证期间的 IPC 稳定性修复

最终全量验证曾两次在既有 `SingleInstance.send_paths()` 首次连接处失败，而对应 IPC 用例单独运行立即通过，证据指向 Windows `QLocalServer` 刚 listen 后的瞬时连接失败。先增加 `test_send_paths_retries_transient_connect_failure`，确认旧实现 RED；随后将 send 路径改为最多三次创建 socket/连接、短间隔重试。IPC 文件全量 `10 passed in 1.36s`，最终项目全量 `87 passed in 10.78s`。

### 剩余顾虑

- QWebEngineView/Chromium 仍按要求不在 offscreen 测试中实例化；默认 factory 的 base URL 计算和注入接口已自动测试。
- 真实 Office COM 仍依赖装有 Office 的交互式 Windows 环境；本次自动测试覆盖 Office backend contract、worker 串行化和临时 artifact 消费，没有启动真实 Office 应用。

---

## 共享 completion Critical 修复（2026-08-21）

### 根因

ReaderApp 的多个 MainWindow 共享同一个 `PreviewExecutor.completed` 广播信号。旧 `_preview_completed()` 在确认 document id 归属前调用 `take_completion()`，因此连接顺序靠前但不拥有该 document 的窗口会先取走 completion；若结果带私有 PDF artifact，还会把另一窗口需要的副本清理掉。

### RED

先增加确定性双窗口测试：第一窗口先创建并保持打开，其 worker 阻塞；第二窗口任务排队。释放第一任务后，两个 completion 按串行 pool 完成。旧实现表现为第一窗口显示正确内容，但第一窗口随后取走第二窗口 completion，第二窗口一直停留在 loading。

同时增加缺失 worker output 错误页和独立 executor registry 回收测试：

```text
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_window.py::test_shared_executor_delivers_each_result_only_to_owner_window tests/test_window.py::test_missing_worker_output_becomes_target_tab_error tests/test_window.py::test_idle_standalone_executor_leaves_qapp_registry -v
```

结果：`3 failed`，分别对应共享 completion 被错误消费、`assert output is not None`、qapp registry 永久保留独立 executor。

### GREEN

- `_preview_completed()` 先查本窗口 `_documents`；非 owner 不调用 `take_completion()`，直接返回。
- owner 在 take 前检查 closing/page identity；只有 owner 可以消费或清理对应 completion。
- 缺失 output 不再 assert，而是在目标 tab 显示“未返回预览结果”错误页。
- 独立 MainWindow 的 executor 记录 qapp registry；窗口关闭时请求 idle release。无任务则立即移除并 `deleteLater()`，有运行任务则由 completion GUI slot 在 registry/pending 清零后安全移除。
- closeEvent 仍只遍历并 cancel 当前窗口自己的 document ids。
- 增加文件名 tab title 断言。

定向 RED 三测试修复后：`3 passed in 3.29s`。

### Artifact 隔离证据

双窗口测试让第二窗口返回 PDF。修复后两个窗口分别从 loading 变为 `WINDOW ONE` / `WINDOW TWO`，第二窗口 viewer 收到的 per-document 私有 PDF 仍存在且不同于源 PDF，证明第一窗口既未消费 completion，也未删除另一窗口 artifact。

### 最终验证

- `tests/test_window.py`：26 passed in 7.35s
- `tests/test_office.py tests/test_ipc.py tests/test_cache.py`：32 passed in 2.57s
- 全量：90 passed in 11.03s
- IDE lint：无诊断
