# Final Important Fix Report

日期：2026-08-24  
基线 HEAD：`525f2cc5dab431936135a8535a0beb6bd33aaafa`  
工作目录：`C:\Research\AgentDevelopor\READER`

## 状态

最终整分支审查列出的 6 组 Important 均已按测试先行方式修复。生产代码、回归测试和本报告纳入新提交；`dist/`、`build/` 未纳入提交。

## 修复摘要

1. Active window IPC
   - `ReaderApp` 从 `QApplication.activeWindow()` 沿 parent 链定位所属 `MainWindow`。
   - 目标必须仍属于 `_windows` 且非 closing；无 active 时回退到最近的 eligible window；没有 eligible window 时创建新窗口。
   - 覆盖两个窗口焦点回 A、active child dialog 回溯 parent 两种情况。

2. Closing lifecycle
   - `MainWindow.closeEvent()` 一开始设置 closing 并同步通知 `ReaderApp` 移除窗口。
   - 最后 eligible window 关闭时立即释放 IPC server/lock，不再等待 `destroyed`。
   - `open_paths()`、`_start_preview()` 对 closing window 为 no-op。
   - drop 使用对象身份而非 `id()`，避免迟到 `destroyed` 重复 drop 或误删后建窗口。
   - 新增 `MainWindow.is_closing()`；状态提示仅新增最小 `show_status()` helper。

3. IPC application ACK
   - 请求帧保持原有 4-byte 长度头 + UTF-8 JSON list，不改 Unicode、large frame 和 chunked framing。
   - server 仅在完整解析且 callback 成功返回后发送固定 `b"ACK"`。
   - client 必须先排空请求，再收到完整 ACK 才返回 `True`；无 ACK、callback 异常、超时均返回 `False`。
   - server ACK 排空最多 3 轮、每轮 100 ms；避免 GUI thread 无界等待。
   - secondary 发送失败时 stderr 输出诊断并返回码 2。

4. Shell side effects / hint
   - `create_desktop_shortcut()` 默认保留已存在的 `Reader.lnk`，不会 Dispatch/Save。
   - 新增 keyword-only `overwrite=False`，显式 `True` 时允许重建，原调用签名兼容。
   - association 与 shortcut 异常分别捕获；窗口已创建后在 status bar 显示“文件关联设置失败”或“桌面快捷方式创建失败”，应用继续运行。

5. Windows icon location
   - 新增 `_icon_location()`，无空格保持 `C:\Reader\Reader.exe,0`。
   - 有空格生成 `"C:\Program Files\Reader\Reader.exe",0`。
   - 只把末尾 `,<整数>` 识别为既有 index；路径中的普通逗号不再误判。
   - registry `DefaultIcon` 与 shortcut `IconLocation` 共用该 helper。

6. Office HTML fallback
   - PDF export 失败但 HTML SaveAs 成功时保留 export dir，并设置 `PreviewResult.asset_dir`。
   - viewer base URL 使用该目录，可解析相对图片等资源。
   - HTML asset dir 进入窗口 artifact pin 生命周期；切回 builtin、关闭 tab/window、替换结果时清理。
   - 带外部相对资源的 HTML 不写入仅保存 HTML 字符串的 cache，避免 cache hit 丢失资源目录。
   - PDF 与 HTML 均失败时异常继续传播；窗口保留 builtin 内容并显示 Office 导出失败状态。

## TDD RED / GREEN 证据

每组均先增加测试并观察预期失败，再写最小生产修复：

- Active IPC RED：两个新测试均把路径错误投递到最近窗口 B；GREEN：2 passed。
- Closing RED：缺少 `is_closing()`，且 lifecycle/no-op 断言失败；GREEN：4 passed。
- ACK RED：client 未读取 ACK、无 ACK 仍返回 True、server 不写 ACK、callback 异常外泄；GREEN：完整 IPC suite 23 passed。
- secondary 返回码 RED：发送失败仍返回 0；GREEN：main launch suite 18 passed。
- Shell/icon RED：缺少 `_icon_location`、shortcut 覆盖已有文件、异常被静默吞掉；GREEN：associate 16 passed、main launch 18 passed。
- Office HTML RED：`asset_dir is None` 且 export dir 被删除；GREEN：Office backend 10 passed。
- HTML pin/cache RED：切回 builtin 后 export dir 未删除，且带资源 HTML 被错误写 cache；GREEN：相关窗口测试 3 passed。
- ACK GUI bound RED：server 使用 1000 ms wait；GREEN：限制为每轮 100 ms。

## 测试

- 相关 focused suite：
  - `154 passed in 47.82s`
- IPC process race，独立执行 3 次：
  - `1 passed in 16.50s`
  - `1 passed in 16.76s`
  - `1 passed in 16.51s`
- 全量（最终 ACK bound 测试前）：
  - `195 passed in 49.65s`
  - `195 passed in 47.37s`
- 最终生产改动后全量：
  - `196 passed in 46.93s`
- 最终 IPC suite：
  - `23 passed in 25.42s`
- IDE lint：修改文件无诊断。

## Clean build 与 frozen smoke

- 最终 clean build：
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1`
  - exit 0；PyInstaller 6.22.2 / Python 3.12.10。
- 最终实际 frozen multi-batch smoke：
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe -TimeoutSeconds 45`
  - 两批各 2 个 Markdown 路径均以精确 JSON batch 到达 primary。
  - `Reader GUI smoke passed: primary PID 24936, exact two 2-file batches`
- 最终产物：
  - `dist\Reader\Reader.exe`
  - size：`5,870,536 bytes`
  - SHA-256：`61CC34BC9A3971C3AC59A1D05A51125A30C426D0B45325C57F770DA2830D8884`
  - onedir：`3,057 files`，`606,027,163 bytes`
- 清理复核：
  - exact Reader.exe processes：0
  - `reader-gui-smoke-*` roots：0
  - `Reader.SingleInstance.v1.gui-smoke-*.lock`：0

## Concerns

- PyInstaller 仍报告宿主 PySide6 缺少未使用的 `qmlassetdownloaderprivateplugin.dll`；与既有构建相同，build 和实际 WebEngine GUI smoke 均通过。
- frozen smoke 通过应用层 telemetry 证明两批参数成功 ACK/到达，但不读取 Qt 内部 tab 文本；active-window、closing、HTML asset 生命周期由确定性窗口测试覆盖。
- 构建产物未签名；签名不在本次修复范围。
