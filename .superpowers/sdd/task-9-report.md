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
