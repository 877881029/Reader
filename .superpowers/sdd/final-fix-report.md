# PPTX 最终审查修复报告

日期：2026-08-26
基线：`b4a97dd`（`main == origin/main`）
范围：保留并完成中断状态下的全部未提交 PPTX 修复；未 reset、checkout 或丢弃用户改动。

## Status

最终审查的三项目标均已实现并验证：

1. 默认打开 PPTX 只启动本地 visual preview，不探测或调用 Office COM。Office action 在 availability unknown 时可点击，pending 时禁用；检测成功后继续 Office 请求，失败则保持当前内容。
2. 文本模式或 Office 请求失败时，恢复请求前的同一 widget、mode、status 和必要的 visual signal 连接。preview 与 Office availability 使用独立单线程 pool；关闭、取消和迟到结果受 document identity、generation、request ownership 与 closing guards 保护。
3. WebEngine `file:` allowlist 只允许 source 的精确 canonical 文件及 bundle canonical realpath 根。路径比较使用 Windows `normcase(realpath)`；sibling、parent、`..`、symlink escape 和其他 file URL 均阻断。真实 bundle 完成加载后的 blocked 初始快照为空。

保留了中断实现中的低成本 UI 改进：中文上一页/下一页/适合窗口 toolbar，以及居中 letterbox 布局；源码与生成 bundle 一致。

## 关键修复

- Office availability probe 从 preview pool 分离，避免被慢 preview 阻塞。
- 去掉 availability result 的第二层 queued delivery，消除 worker 已 idle 但 UI 仍显示“正在检测”的竞态。
- 请求记录保存 previous mode/status；所有非初始 text/office/viewer 错误统一恢复旧内容，不用错误 label 替换可用 widget。
- 失败后只为仍在 layout 中的 visual widget 重绑一次 signal；重复 Office 失败不累积连接。
- `OfflineRequestInterceptor` 注入 source 与 bundle root；file 请求先 canonicalize，再做 source equality 或 bundle containment。
- WebEngine 集成探针 deadline 调整为 15 秒，以覆盖本机软件 compositor 冷启动；resize 测试使用屏幕范围内的 900×650 → 1200×800，避免 150% DPI 下窗口被系统钳制导致假失败。

## Tests

- `tests/test_pptx_view.py -v`：17 passed。
- `tests/test_window.py -v`：92 passed。
- `tests/test_pptx_webengine.py -v`：连续两轮均 3 passed；使用 `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu` 适配当前宿主 GLES context 不可用。
- Web：24 passed。
- npm typecheck：通过。
- npm build：通过；生成 `index-BQR8aOSp.js`、`index-pQyMqwqd.css`，旧 hash 已删除。
- Python 全量：263 passed, 1 skipped。
- `git diff --check`：提交前最终执行。

## Build / smoke

- clean `scripts/build_windows.ps1`：exit 0。
- notice 从 `web/pptx-viewer/THIRD_PARTY_NOTICES.txt` 直接复制。
- source/frozen `manifest.sha256` SHA256：
  `6e66ec6221fa109fc36cc3f0dadf027828defdfaeeb9ed335c0f914a5ca8949b`
- frozen `scripts/smoke_windows.ps1`：通过。
  - Phase A：真实四页 fixture，`visual-ready slides=4`。
  - Phase B：两批各 2 文件 IPC 精确到达。
- `dist/Reader/Reader.exe`：
  - size：5,885,743 bytes
  - SHA256：`80f9e97f5bcdbe873f1673df06c9e62b13491ff191e158521423d4e4f2722e35`
- `C:\Users\runqyang\Desktop\Reader.lnk` 已覆盖刷新并验证：
  - target：`C:\Research\AgentDevelopor\READER\dist\Reader\Reader.exe`
  - working directory：`C:\Research\AgentDevelopor\READER\dist\Reader`
  - icon：`C:\Research\AgentDevelopor\READER\dist\Reader\Reader.exe,0`

## Concerns

- npm audit 报告 3 个上游依赖漏洞（1 moderate、1 high、1 critical）；本次锁定依赖与功能范围未升级，不能直接执行 breaking `npm audit fix --force`。
- PyInstaller 继续报告宿主 PySide6 缺少未使用的 `qmlassetdownloaderprivateplugin.dll`；clean build 与真实 frozen visual smoke 均通过。
- 当前宿主 GPU 无法创建 Chromium GLES shared context；真实集成测试以 `--disable-gpu` 软件 compositor 通过，frozen smoke 使用正常产品启动路径通过。
- 产物未签名；签名不在本次范围。
