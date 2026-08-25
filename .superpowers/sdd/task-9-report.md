# PPTX Task 9 报告：Separate Frozen Visual Smoke and Final Regression

## 状态与基线

- 状态：完成。
- 指定基线与执行前 `HEAD`：
  `f80a17c77ff099f4868defa4bd201f1954aed790`。
- 工作区：`C:\Research\AgentDevelopor\READER`。
- 按用户要求：只提交，不 push，不修改 git config。

## 实现

### 持久 visual-ready telemetry

- `reader.smoke.append_visual_ready(path, slides)` 仅在
  `READER_SMOKE_VISUAL_LOG` 非空时启用。
- 每次写入一条 UTF-8 JSONL：
  `path/kind=pptx/slides/status=ready`。
- 写入后显式 `flush()` 和 `os.fsync()`；默认禁用时不创建文件。
- `MainWindow` 只在 document identity、generation、widget、visual mode、
  layout ownership 和 closing guards 全部通过后记录。
- tab 关闭或 view 替换后的迟到 ready 不更新状态、不记录 telemetry。

### 两个不重叠的 frozen 生命周期

- Phase A：
  - 只启动 `$visualProcess`；
  - 打开真实四页 fixture
    `tests\fixtures\pptx\visual-elements.pptx`；
  - 使用独立固定 60 秒 visual deadline；
  - 等待精确 `ready/slides=4`，并拒绝 `renderer-failure`；
  - 停止 Reader 与 QtWebEngine 完整进程树、等待退出；
  - 删除 visual IPC namespace、lock、Chromium profile 与隔离根。
- Phase B：
  - 仅在 Phase A 退出并清理成功后创建全新 `$ipcPrimary`；
  - 保持既有两批、每批两文件的 IPC 到达与单实例断言；
  - 不复用 `$visualProcess`，脚本中不存在旧 `$primary` 变量。
- 业务错误与 cleanup 错误继续由 `Resolve-SmokeFailure` 合并，业务原始错误优先。

### GPU 驱动缓存清理

实际 frozen smoke 首轮已成功收到 `slides=4`，但 AMD 常驻驱动长期持有重定向
`LOCALAPPDATA\AMD\DxCache`。禁用 GPU 与强制 SwiftShader 探针都能正常渲染四页，
但仍会产生 AMD/D3D 驱动缓存锁，证明问题不在 Reader/QtWebEngine 子进程退出。

最终 Phase A 复用主机系统 GPU cache 路径，避免把系统驱动缓存放入必须删除的
visual profile；Reader/Chromium 的 `USERPROFILE`、`APPDATA`、显式
Chromium user-data-dir、TEMP/TMP 与 IPC namespace 仍全部隔离。Phase B
不使用 WebEngine，继续保持原有完整 `LOCALAPPDATA` 隔离。

## TDD 证据

### 首轮 RED

命令：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_smoke.py tests/test_window.py::test_late_visual_ready_after_close_is_not_logged tests/test_window.py::test_current_visual_ready_is_logged_after_state_update tests/test_packaging.py::test_windows_gui_smoke_script_declares_strict_telemetry_and_cleanup -v
```

结果：`5 failed, 3 passed`。失败准确命中：

- `append_visual_ready` 不存在；
- `reader.shell.window.append_visual_ready` 未导入/调用；
- smoke 脚本没有 visual telemetry 和分离 Phase A/Phase B。

### 首轮 GREEN

同一命令结果：`8 passed in 5.79s`。

### 清理问题 RED/GREEN

- RED：静态回归要求扩展 cleanup 条件等待，`1 failed`。
- GREEN：`1 passed`。
- 实机仍证明驱动锁是长期常驻而非普通释放延迟后，增加 Phase A 主机 GPU cache
  路径契约：
  - RED：`1 failed`；
  - GREEN：`1 passed`。
- 最终实机 smoke 通过，并证明 visual/ipc 根都已删除。

## 最终验证

### Web

- `npm.cmd --prefix web/pptx-viewer test`
  - `3 passed` test files；
  - `23 passed` tests。
- `npm.cmd --prefix web/pptx-viewer run build`
  - TypeScript typecheck 通过；
  - Vite build 通过。

### Python

- `.venv\Scripts\python.exe -m pytest -v`
  - 最终复验：`255 passed, 1 skipped in 98.48s`；
  - skip 为显式 opt-in 的真实 npm stale-asset 测试。
- 修改文件 IDE lint：无诊断。

### Clean build

- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1`
  - 退出码 `0`；
  - npm ci/build、source/frozen manifest 校验、PyInstaller clean onedir 全部通过；
  - 已知 warning：未使用 QML
    `qmlassetdownloaderprivateplugin.dll` 缺失，不影响构建或后续 WebEngine smoke。
- npm audit 报告 3 个现有依赖漏洞（1 moderate、1 high、1 critical）；本任务未执行
  可能改变锁定依赖的 `npm audit fix --force`。

### Frozen smoke

命令：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe
```

结果：退出码 `0`。

- Phase A：
  `{"kind":"pptx","slides":4,"status":"ready"}`。
- Phase B：
  两批 JSONL 均精确包含各自两个 Markdown 路径。
- 最终：
  `ReaderProcesses=0`、
  `VisualRootExists=False`、
  `IpcRootExists=False`。

## 版本与哈希

- `pptx-viewer`：`0.2.2`。
- `fflate` lock 解析版本：`0.8.3`。
- Node.js：`22.22.0`。
- npm：`11.15.0`。
- PySide6：`6.11.2`。
- PyInstaller：`6.22.2`。
- bundle `manifest.sha256` 文件 SHA256：
  `F6F32AA6416717BB47AEBCD4F365CC976DD01C24D86A8E768A12B70042FC2633`。
- `dist\Reader\Reader.exe`：
  - 大小：`5884468 bytes`；
  - SHA256：
    `1A40CB1760499C44D73283895A83752AE0DD4FC84AA96E2412F97DFD9EAC0219`。

## 桌面快捷方式

最终 smoke 和哈希确认后，已覆盖刷新：

- 路径：`C:\Users\runqyang\Desktop\Reader.lnk`；
- Target：
  `C:\Research\AgentDevelopor\READER\dist\Reader\Reader.exe`；
- WorkingDirectory：
  `C:\Research\AgentDevelopor\READER\dist\Reader`；
- IconLocation：
  `C:\Research\AgentDevelopor\READER\dist\Reader\Reader.exe,0`；
- Arguments：空。

## 下一步

由用户使用真实日常 PPTX 验收视觉保真、导航缩放、文本回退和 Office 高保真切换；
若出现兼容问题，以最小真实 fixture 增加回归。
