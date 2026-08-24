# UX Task 9 报告：Full UX and Packaging Regression

## 状态与基线

- 状态：完成。
- 指定基线与执行前 `HEAD`：
  `38757e50859afdec3bbcca1ee17f7fdc034c3ee1`。
- 工作区：`C:\Research\AgentDevelopor\READER`。
- 环境：Windows 11 `10.0.26100`、Python `3.12.10`、PySide6
  `6.11.2`、PyInstaller `6.22.2`。

## 新增回归与修复

- `tests/test_window.py`
  - 新增最终跨功能验收，覆盖 1200x800、800x500 minimum、Ctrl+O、
    blank `+` 替换、多 tab、同批重复路径聚焦、builtin-first，以及 Office
    切换失败后保留 builtin 内容。
  - 既有测试继续覆盖实际居中调用、32px cascade、Open multi-select、drop、
    COM 不可用、切换回 builtin、Office 迟到结果隔离、IPC 完整批次。
- `tests/test_pipeline.py`
  - 对 `.docx/.pptx/.xlsx` 统一断言默认 builtin-first，既不调用
    `available_for()`，也不调用 `export()`。
- `tests/test_associate.py`
  - 最终验证 packaged `Reader.exe` 的 open command 与 `DefaultIcon=<exe>,0`，
    且不写 `UserChoice`、不回退到 `reader.cmd`。
- `tests/test_icon_assets.py`
  - PNG 与 ICO 每个尺寸都必须同时保留 alpha 0 和 alpha 255。
- `tests/test_packaging.py`、`scripts/smoke_windows.ps1`
  - 新增可重复的 frozen GUI smoke；隔离 profile、IPC namespace，并设置
    `READER_SKIP_SHELL_INTEGRATION=1`。
- `src/reader/shell/window.py`
  - 修复同一批次 `[first, second, first]` 的重复路径聚焦顺序：先创建
    `to_open` 标签，再执行 `to_focus`。

## RED / GREEN 证据

1. GUI smoke 自动化先写测试：
   - 命令：
     `.venv\Scripts\python.exe -m pytest tests\test_packaging.py::test_windows_gui_smoke_is_isolated_multi_batch_and_self_cleaning -v`
   - RED：`1 failed`，准确原因是
     `scripts/smoke_windows.ps1` 不存在。
   - 新增脚本后 GREEN：`1 passed`。
2. 最终跨功能窗口验收：
   - 命令：
     `.venv\Scripts\python.exe -m pytest tests\test_window.py::test_ux_packaging_regression_multi_open_duplicate_blank_and_office_failure -v`
   - RED：Office action 等待超时。根因是同批重复路径在标签创建前尝试聚焦，
     实际焦点留在 Markdown 标签。
   - 最小生产修复后 GREEN：`1 passed`。
3. 其余新增测试属于 Tasks 1-8 已实现接口的最终聚合回归，因此首次执行即
   GREEN；它们用于防止跨特性退化，不伪造 RED。

## 准确命令与结果

### 修改前基线

- `.venv\Scripts\python.exe -m pytest -v`
- 结果：`158 passed in 43.04s`。

### 聚焦回归

- `.venv\Scripts\python.exe -m pytest tests\test_window.py::test_ux_packaging_regression_multi_open_duplicate_blank_and_office_failure -v`
- 结果：`1 passed in 5.96s`。
- `.venv\Scripts\python.exe -m pytest tests\test_pipeline.py tests\test_associate.py tests\test_icon_assets.py tests\test_packaging.py tests\test_ipc.py -v`
- 结果：`54 passed in 27.60s`。

### 两轮全量 / flake 检测

- 第 1 轮：`.venv\Scripts\python.exe -m pytest -v`
  - `165 passed in 44.51s`。
- 第 2 轮：`.venv\Scripts\python.exe -m pytest -v`
  - `165 passed in 42.29s`。
- 结论：两轮收集项和结果一致，未观察到 flake。

### 图标幂等与打包静态复验

- 运行 `scripts\generate_icons.py` 前后，对 `assets\icons` 全部文件执行
  SHA-256 集合比较；命令退出码 0，无差异。
- `.venv\Scripts\python.exe -m pytest tests\test_packaging.py tests\test_icon_assets.py -v`
- 结果：`12 passed in 0.63s`。
- 关键图标哈希：
  - `reader.ico`：
    `F68CA2425586D6CF2CE403127F1CDF7812AD87629C54D655D02DF0154E5FC32C`
  - `reader-r.svg`：
    `F8396B8133452845C2271608DB652AD4FFAE4AF34E035E2637D8814BF7B8A3AB`

### Clean build

- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1`
- 结果：退出码 0，PyInstaller clean onedir build 成功。
- 构建验证：
  - ProductName：`Reader`
  - FileDescription：`Reader`
  - onedir 文件数：`3057`
  - onedir 总大小：`606023573 bytes`
- PyInstaller 输出一条缺失未使用 QML
  `qmlassetdownloaderprivateplugin.dll` 的 warning；构建成功，后续 GUI/WebEngine
  smoke 通过。

### Frozen GUI smoke

- 命令：
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe -TimeoutSeconds 45`
- 结果：
  `Reader GUI smoke passed: primary PID 3104, two 2-file batches`。
- 自动验证：
  - 使用独立 `USERPROFILE/APPDATA/LOCALAPPDATA`。
  - 使用随机 `READER_IPC_NAMESPACE`。
  - 使用 `READER_SKIP_SHELL_INTEGRATION=1`，不修改真实 association/shortcut。
  - 首次启动传两个 `.md` 样本文档。
  - `MainWindowHandle != 0`，primary 存活。
  - 通过 `Get-CimInstance Win32_Process` 按完整 exe 路径确认仅一个
    `Reader.exe`。
  - 第二次 exe 启动传另一批两个 `.md`，secondary 退出码 0，原 primary
    仍存活且仍是唯一 `Reader.exe`。
  - `finally` 递归停止进程树并删除隔离目录；结束后同路径
    `Reader.exe` 进程数为 0。

## 产物

- 路径：
  `C:\Research\AgentDevelopor\READER\dist\Reader\Reader.exe`
- 大小：`5866946 bytes`
- SHA-256：
  `8AD4FFA168FB34493E0A0718CFBF4E806674EE4DAFC2328B443BAD8550DA39CC`
- `dist/` 与 `build/` 均受 `.gitignore` 保护，不纳入提交。

## 已知限制

- frozen smoke 使用无侵入的进程/窗口句柄检查，没有读取 Qt 内部 tab 文本；
  两批多参数和 tab 创建由窗口/IPC 代码级回归证明，exe smoke 证明真实冻结程序的
  单进程、窗口存活、secondary 转发退出及清理。
- smoke 的四个样本文档均为 Markdown；Office builtin-first、COM 不可用、
  Office 失败保留、迟到结果安全由确定性代码级测试覆盖，避免 GUI smoke 依赖主机
  Office 安装状态。
- 构建产物未签名；签名不在本任务范围内。

---

## Important 纠正与补强（2026-08-24）

本节取代上文对首版 frozen smoke 的充分性结论。首版仅观察到 secondary
退出码 0、primary 窗口存活和单进程，不能证明第二批路径真正到达应用层；首版
`Remove-Item -ErrorAction SilentlyContinue` 也可能把清理失败误报为成功。

### 严格 RED 证据

1. telemetry、启动顺序、IPC callback 与脚本声明测试：
   - 命令：
     `.venv\Scripts\python.exe -m pytest tests\test_smoke.py tests\test_main_launch.py::test_primary_launch_records_initial_batch_after_server_ownership tests\test_window.py::test_initial_and_ipc_batches_are_logged_separately_before_open tests\test_packaging.py::test_windows_gui_smoke_script_declares_strict_telemetry_and_cleanup tests\test_window.py::test_mixed_cross_batch_open_adds_new_tab_then_focuses_existing tests\test_window.py::test_duplicate_while_original_is_loading_focuses_original_without_new_tab tests\test_window.py::test_duplicate_path_is_case_insensitive_on_windows -v`
   - 结果：`5 failed, 3 passed`。
   - 预期失败：缺少 `reader.smoke`、primary 初始批次未记录、IPC callback
     未记录、脚本未声明 telemetry/严格清理。
   - 三个重复路径测试首次即通过，因为上一提交的“先 open 后 focus”修复已经满足
     行为；本次将缺口固化为明确回归。
2. frozen smoke 严格验收第一次失败：
   - `Initial two-path batch was not logged exactly`。
   - telemetry 实际存在；根因是 Windows PowerShell 5.1 将管道中的 JSON
     数组包装成单个 `Object[]`，脚本严格比较误判。拆分
     `ConvertFrom-Json` 与数组赋值后修复。
3. frozen smoke 严格验收第二次失败：
   - 日志仅有第一批，第二批在 45 秒内未到达。
   - 新增 RED：
     `.venv\Scripts\python.exe -m pytest tests\test_main_launch.py::test_secondary_uses_instance_ownership_without_empty_server_probe -v`
   - 结果：`1 failed`，明确命中 `_server_running()` 空 payload 预连接。
   - 根因：secondary 在真实发送前先建立无帧探针，primary 会在 GUI 线程等待空帧；
     旧 smoke 只检查 secondary 退出码，且启动代码没有验收到达结果，因此掩盖了
     丢批次。修复为直接创建 `ReaderApp`、通过实例锁确定 primary/secondary，
     secondary 再发送唯一真实批次，不再建立空探针连接。

### telemetry 行为

- 新增 `reader.smoke.append_smoke_batch(paths)`：
  - 仅当 `READER_SMOKE_BATCH_LOG` 非空时启用。
  - 每批执行一次 UTF-8 JSON 行追加，保留批次原子性和参数顺序，并 flush/fsync。
  - 环境变量缺失时立即返回，不创建文件、不探测路径、无正常用户副作用。
  - 显式启用但写入失败时抛出 `OSError`；startup 返回 2，IPC callback 输出诊断、
    请求应用退出且不继续 open。
- primary 成功持有 server 后先记录初始 argv 批次，再创建窗口/open。
- IPC callback 先记录收到的完整批次，再调用窗口 `open_paths(paths)`。
- 单元测试覆盖默认禁用、UTF-8 两行精确 JSON、写失败传播、initial + IPC
  分行记录，以及 callback 调用 open 前日志已经可见。

### 严格 smoke 与清理

- 脚本隔离：
  `READER_IPC_NAMESPACE`、`READER_SMOKE_BATCH_LOG`、`USERPROFILE`、
  `APPDATA`、`LOCALAPPDATA`、`TEMP`、`TMP`、Chromium profile 和
  `READER_SKIP_SHELL_INTEGRATION=1`。
- 第一批启动后等待第 1 行精确等于两个路径；第二次 exe 退出码为 0 后等待第 2
  行精确等于第二批两个路径；日志必须恰好两行。
- 单进程计数排除启动前同路径 Reader PID；清理只处理本次 primary、所有保存的
  secondary、新增同路径 Reader 及其后代，不杀启动前用户进程。
- cleanup 先 terminate、再对残留 PID force kill，`WaitForExit` 并轮询进程树
  清零；恢复环境后删除隔离 TEMP 下的 namespace lock。
- 测试根目录最多重试删除 10 次；最终仍存在则抛出
  `Failed to remove smoke test root`。不再对 `Remove-Item` 使用
  `SilentlyContinue`。
- 最终核验：`RemainingReaderProcesses=0`、`RemainingSmokeRoots=0`。
  另清除了首版脚本在 19:08 遗留的旧 Task 9 smoke 目录。
- `test_windows_gui_smoke_script_declares_strict_telemetry_and_cleanup` 仅验证脚本
  关键声明和严格清理 token，不声称执行 PowerShell；真实执行证据如下。

### 最终 clean build 与实际 frozen smoke

- clean build：
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1`
  - 退出码 0；构建分析明确包含 `reader.smoke`。
- 实际命令：
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe -TimeoutSeconds 45`
- 实际日志：
  - Batch 1：
    `["C:\\Users\\runqyang\\AppData\\Local\\Temp\\reader-gui-smoke-ff235b9e92bd4954967d06cf05ffad49\\samples\\batch-one-a.md","C:\\Users\\runqyang\\AppData\\Local\\Temp\\reader-gui-smoke-ff235b9e92bd4954967d06cf05ffad49\\samples\\batch-one-b.md"]`
  - Batch 2：
    `["C:\\Users\\runqyang\\AppData\\Local\\Temp\\reader-gui-smoke-ff235b9e92bd4954967d06cf05ffad49\\samples\\batch-two-a.md","C:\\Users\\runqyang\\AppData\\Local\\Temp\\reader-gui-smoke-ff235b9e92bd4954967d06cf05ffad49\\samples\\batch-two-b.md"]`
  - `Reader GUI smoke passed: primary PID 12732, exact two 2-file batches`
- 最终产物：
  - 路径：`C:\Research\AgentDevelopor\READER\dist\Reader\Reader.exe`
  - 大小：`5868125 bytes`
  - SHA-256：
    `BFDF68AFE07E875C1244C98B00E77BC2E76EFF974274F6E70C6015DA633ECAE7`

### 最终回归

- 聚焦：
  `.venv\Scripts\python.exe -m pytest tests\test_smoke.py tests\test_main_launch.py tests\test_packaging.py tests\test_window.py -v`
  - `80 passed in 15.44s`（在移除空探针前；新增空探针回归随后独立 GREEN）。
- 全量第 1 轮：`.venv\Scripts\python.exe -m pytest -v`
  - `174 passed in 40.41s`。
- 全量第 2 轮：`.venv\Scripts\python.exe -m pytest -v`
  - `174 passed in 47.05s`。
- 两轮收集数与结果一致，未观察到 flake；IDE lint 无诊断。

### 剩余限制

- frozen telemetry 证明两批 argv 在 primary 应用层按原子批次和原顺序到达，并且
  callback 在调用 `open_paths` 前完成记录；脚本仍不侵入 Qt tab 内部。
  跨批 mixed duplicate、loading duplicate、Windows 大小写不敏感与批量 tab
  创建由代码级窗口回归证明。

---

## Important：finally 不覆盖业务原始错误（2026-08-24）

### RED 与错误四象限

- 新增可独立 dot-source 的 `scripts/smoke_helpers.ps1`，提供
  `Resolve-SmokeFailure`；`tests/test_packaging.py` 真实启动 Windows PowerShell
  验证无错、仅业务错、仅 cleanup 错、业务与 cleanup 同时发生四种情况。
- RED 命令：
  `.venv\Scripts\python.exe -m pytest tests\test_packaging.py::test_windows_gui_smoke_script_declares_strict_telemetry_and_cleanup tests\test_packaging.py::test_smoke_failure_resolver_preserves_business_error_before_cleanup -v`
  - 结果：`2 failed`。
  - 静态测试命中脚本缺少 `$smokeError`；可执行测试命中 helper/函数不存在。
- GREEN 同命令：`2 passed in 2.09s`。两错并发时，PowerShell 进程按预期非零退出，
  输出先包含 `business-original`，随后包含 `cleanup-appended`。

### 主体错误决议

- `catch` 仅保存原始 `ErrorRecord` 到 `$smokeError`。
- `finally` 中 telemetry 诊断、进程停止、环境恢复、namespace lock 删除和测试根
  删除均各自捕获并追加到 `$cleanupFailures`，`finally` 本身不再 `throw`。
- `finally` 之后调用 `Resolve-SmokeFailure`：
  - 无错返回 `$null`；
  - 仅业务错误返回原始 `ErrorRecord`，保留原异常上下文；
  - 仅 cleanup 错误生成 cleanup `ErrorRecord`；
  - 两者同时生成组合 `ErrorRecord`，消息第一行是原始业务异常，之后追加 cleanup
    诊断。
- 只有统一决议确认无错误后才输出 `Reader GUI smoke passed`。

### 安全清理、实际 smoke 与回归

- 仅处理精确旧 namespace
  `gui-smoke-6b5a1ce89d7d4e1899ba1be18db93ea2`：旧根目录已不存在，
  删除其精确 lock
  `Reader.SingleInstance.v1.gui-smoke-6b5a1ce89d7d4e1899ba1be18db93ea2.lock`；
  复核 `ExactLegacyNamespaceRemaining=0`，未删除其他 Reader namespace。
- 未 rebuild frozen exe。使用已有 `dist\Reader\Reader.exe` 实际运行：
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe -TimeoutSeconds 45`
  - `Reader GUI smoke passed: primary PID 46184, exact two 2-file batches`
  - 本次 namespace：`gui-smoke-76e5b6a612744c07be69c0c6a62dcee5`
  - 清理复核：`LatestSmokeArtifactsRemaining=0`、`ReaderProcessesAtRest=0`。
- packaging 聚焦：`8 passed in 6.06s`。
- Task 9 聚焦：
  `.venv\Scripts\python.exe -m pytest tests\test_smoke.py tests\test_main_launch.py tests\test_packaging.py tests\test_window.py -v`
  - `82 passed in 24.42s`。
- 全量：`.venv\Scripts\python.exe -m pytest -v`
  - `175 passed in 45.91s`。
- IDE lint：本次修改文件无诊断。
