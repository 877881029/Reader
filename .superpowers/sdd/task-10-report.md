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
