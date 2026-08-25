# Reader 项目状态（AI 接手必读）

最后更新：2026-08-25  
Git：`main` 应与 `origin/main` 同步；功能边界必须提交并推送。

## 背景

Reader 是 Windows 桌面文档查看器（PySide6）。v1 已支持 `.docx` / `.pptx` / `.xlsx` / `.md`，标签页、内置预览优先、可选 Office COM 高保真、单实例 IPC、PyInstaller onedir `dist/Reader/Reader.exe`、透明蓝色 R 图标。

内置 PPTX 目前仍是 `python-pptx` 抽文本重画 HTML，丢失版式与图片。用户要求默认预览接近 Cursor 插件 PPTX Viewer：真实幻灯片画布，而不是大纲。

## 当前目标（进行中）

**PPTX 视觉预览（不依赖 PowerPoint）：Tasks 1–9 已完成，待用户验收**

- 规格：`docs/superpowers/specs/2026-08-25-pptx-visual-preview-design.md`（已批准）
- 计划：`docs/superpowers/plans/2026-08-25-pptx-visual-preview.md`（已完成并通过计划审查，9 个 TDD 任务）
- 方案：`QWebEngineView` + 本地许可兼容 Web 渲染器；左缩略图、右单页、缩放翻页
- 首版：静态高保真（背景/图片/文本/形状/表格/基础图表）；不做动画/视频/宏
- 禁止复制 `astx-jp.vscode-pptx-viewer` 专有代码
- 文本抽取保留为回退；Office 高保真仍可选

## 已完成

- UX 与打包：窗口 1200×800、空白标签、多开、builtin-first、Office 切换、图标、关联、onedir、IPC、冻结 smoke
- 规格/计划：`docs/superpowers/specs/2026-08-24-reader-ux-packaging-design.md`、`docs/superpowers/plans/2026-08-24-reader-ux-packaging.md`
- 桌面快捷方式已指向 `dist/Reader/Reader.exe`（用户可再要求刷新）
- PPTX Visual Preview Task 1：完成确定性 Web scaffold 与许可基线（`web/pptx-viewer`、锁定 `pptx-viewer@0.2.2`、唯一 runtime 传递依赖 `fflate`〔lock 解析 `0.8.3`〕、`THIRD_PARTY_NOTICES.txt`、输出到 `assets/pptx-viewer/`）
- PPTX Visual Preview Task 2：完成 Viewer 交互基线（`state.ts` + `viewer.ts`），覆盖 empty deck reject、navigation clamp、按钮/键盘/缩略图导航、25%-400% zoom 夹紧、fit 比例计算、0 尺寸安全处理与 `ResizeObserver` 触发重算；新增状态与 DOM 交互测试并通过
- PPTX Visual Preview Task 2（Important 审查修复）：完成多实例焦点隔离与 root 级键盘事件治理；`root.tabIndex=0`、点击控件/缩略图自动 focus、同 root 重复挂载自动 destroy 旧 controller，消除旧闭包监听泄漏风险
- PPTX Visual Preview Task 3：接入 `pptx-viewer@0.2.2` 官方 `loadPresentation` / `renderSlideToElement` / `getThumbnails` 生命周期，保留 master/layout 继承；真实四页 fixture 覆盖图片、表格、图表与缺失字体
- PPTX Visual Preview Task 3：导出 `ViewerBridge` 并完成 Qt WebChannel 启动、`file:` URL 限制、ready/error/slideChanged 上报、单页错误隔离、empty deck 整体错误与幂等 `presentation.cleanup()`；真实离线 bundle 已生成到 `assets/pptx-viewer/`
- PPTX Visual Preview Task 3（Important 审查修复）：`startViewer` 支持 `AbortSignal` 取消加载与挂载后销毁；`main.ts` 保留 controller 所有权并暴露 `window.readerPptxDispose()`，同时处理 pagehide/beforeunload
- PPTX Visual Preview Task 3（Important 审查修复）：`createViewer` 初始化失败会原子移除 listeners、disconnect observer、清除 root ownership 并 rethrow；销毁后 public render 明确报 disposed，double destroy/abort 幂等
- PPTX Visual Preview Task 3 验证：Web 23 tests、TypeScript typecheck/build、Python Web 资源 4 tests、Python 全量 203 tests 全部通过；未改 Python 产品链路
- PPTX Visual Preview Task 4：完成 `PreviewMode` 扩展（`builtin/visual/text/office`）与 `.pptx` 默认 `visual`；`fmt_pptx.to_visual()` 返回 `kind="pptx"` 并携带 `fallback_html`（复用 `to_html`）
- PPTX Visual Preview Task 4：`text` 模式显式返回 HTML（`内置预览（文本模式）`）；`office` 在 `.pptx` 不可用时回退到 visual（不触发 COM 导出）
- PPTX Visual Preview Task 4：建立缓存契约——visual 跳过 cache `get/put` 且不复用旧 builtin HTML/PDF 缓存，text 使用独立 `text` strategy，`PreviewCache.put` 对 `kind="pptx"` 维持拒绝
- PPTX Visual Preview Task 4：保留 worker 完整 `try/_pin_pdf/emit` 控制流；迁移 4 个 builtin `.pptx` FakeCache PDF 用例到 `.docx`（含 reentrancy），避免视觉模式引入误回归
- PPTX Visual Preview Task 4 验证：`tests/test_formats_pptx.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py -v` 共 `100 passed`
- PPTX Visual Preview Task 4（Important 修复）：`to_visual` 异常回退改为固定安全文案，不再暴露异常细节/绝对路径/HTML 片段；`python -m pytest -v` 全量 `208 passed`
- PPTX Visual Preview Task 5：新增 `PptxVisualView` 显式 `start()` 生命周期；构造阶段仅建立互相隔离的 off-the-record profile/page/channel/bridge，不自动 load，15 秒超时且 bundle URL 不携带 source query
- PPTX Visual Preview Task 5：profile 由 QApplication 生命周期资源守卫持有而非 view；显式 shutdown、closeEvent 和遗漏 shutdown 的 destroyed cleanup 均按 interceptor → channel → page → profile 安全释放
- PPTX Visual Preview Task 5：请求拦截器仅放行 `file/qrc/data/blob`，以锁保护 blocked URL 快照且不从 Chromium 线程发 Qt Signal；显式 helper 保证 profile 安装/卸载 interceptor
- PPTX Visual Preview Task 5：显式注册 QtWebChannel qrc 并在 `DocumentCreation/MainWorld` 注入 `qwebchannel.js`；bridge 提供一次 FullyEncoded 的 `sourceUrl`、`testFailSlide` 及 ready/error/slide relay
- PPTX Visual Preview Task 5（Important）：fallback 前断开 load、停止加载、清 scripts、解绑 channel/bridge、关闭 JavaScript，使用空 base URL；超大 fallback 改用固定安全文本，qrc 缺失改为 view 子 QTimer，ready/未启动/销毁后的失败事件不再误触发 fallback
- PPTX Visual Preview Task 5（Important）：删除 shutdown 中假同步 `runJavaScript(readerPptxDispose)`；依赖 pagehide/beforeunload 与 JS context 销毁释放 renderer，换 inert page 后再 unparent/deleteLater，重复 shutdown 幂等
- PPTX Visual Preview Task 5 验证：聚焦 `tests/test_pptx_view.py -v` 为 `16 passed`；Python 全量 `224 passed`；IDE lint 与 `git diff --check` 通过；未接入 MainWindow（留给 Task 6）
- PPTX Visual Preview Task 6：默认 viewer factory 对 `kind="pptx"` 创建 `PptxVisualView`；所有文档内容替换统一经 `_install_document_content`，先绑定 ready/slide/render-failed 事件再 `start()`，所有内容销毁统一经 `_dispose_widget` 调用 `shutdown()` 后 `deleteLater()`
- PPTX Visual Preview Task 6：新增 PPTX 专用“文本模式/视觉模式”动作；手动文本使用独立 `text` 缓存，Office 切回恢复最近 builtin visual/text，Office 失败保留当前内容并回到 `builtin_mode`
- PPTX Visual Preview Task 6：视觉整体失败由 view 内部展示 fallback，窗口状态精确为 `内置预览（视觉渲染失败）` 且保持 visual；ready/slide/failure 事件均受 document identity、generation、widget、mode 与 closing guard 保护
- PPTX Visual Preview Task 6：切换 Office、切换文本/视觉、关闭标签和关闭窗口均显式销毁 visual；补齐 worker 完成、Office 共存/失败、手动模式、缓存、重入与迟到事件测试
- PPTX Visual Preview Task 6 验证：RED 聚焦 `10 failed, 1 passed`（缺失功能符合预期）；窗口完整 `77 passed`（后续补测后为 80 项）；Python 全量 `237 passed`；IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 6（Important）：`_Document` 显式持有 visual signal/slot 连接；restart、rebind、content disposal 均先断开旧连接，反复 Office 失败恢复不再线性堆积 stale generation handler
- PPTX Visual Preview Task 6（Important）：`_install_document_content` 在同步 `start()` 后重新校验 closing、document identity、generation 与 layout ownership；同步关闭 tab/window 会返回失败、清理 output artifact，且不会写 artifact 状态或启动幽灵 Office availability probe
- PPTX Visual Preview Task 6（Important）验证：RED 聚焦 `3 failed, 1 passed, 1 error`（连接存储缺失、同步关闭后仍探测 Office，window 测试 teardown 随后修正）；GREEN 聚焦 `4 passed`、窗口 `83 passed`、Python 全量 `240 passed`；IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 6 按本次用户指令只提交、不推送；本地提交将领先 `origin/main`
- PPTX Visual Preview Task 7：真实四页 fixture 现由 `scripts/generate_pptx_visual_fixture.py` 字节级确定性生成；固定外层 PPTX 与嵌入图表 XLSX 的 ZIP 元数据和 core 时间，fixture SHA256 为 `b93eab8f2a4b77aa8d2a3eca02941f27be59c118c2092a5528d6743dc5d43321`
- PPTX Visual Preview Task 7：新增真实 QWebEngine 集成覆盖主题背景、PNG `<image>`、`foreignObject table`、基础 chart 结构、缺失字体、四缩略图/首选中、六键导航、缩略图点击、zoom/fit 和 stage resize
- PPTX Visual Preview Task 7：真实 Chromium 请求验证 HTTP/HTTPS/WS/WSS 全由 `OfflineRequestInterceptor` 记录并阻断；测试仅临时绕过第一层 local-content remote policy 以直接验证第二层，产品默认仍保持 remote access 关闭
- PPTX Visual Preview Task 7：constructor-only `test_fail_slide` 经 WebChannel 注入且不进入 query；单页故障显示占位后可继续渲染其他页，无整 deck fallback
- PPTX Visual Preview Task 7：真实 `MainWindow` 默认工厂加载四页并在关闭时释放 off-the-record profile；缺失 bundle/`QtWebEngineProcess.exe` 或进程启动失败显式 skip，注册 `webengine` marker
- PPTX Visual Preview Task 7 验证：RED `2 failed, 2 passed`（generator 不支持输出/不确定、DOM 元素类型探针缺失）；GREEN 聚焦 `20 passed`；npm `23 passed`；Python 全量 `244 passed`；npm typecheck/build、IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 7 按本次用户指令只提交、不推送、不修改 git config
- PPTX Visual Preview Task 7（Important 审查修复）：zoom/fit 改为解析百分比并校验 `+10`、25%–400% 范围及 transform；真实 host 同时断言 `Inherited title` 与 `#14305A` 背景 paint；网络注入前 snapshot 必须为空，注入后规范化集合必须精确等于 HTTP/HTTPS/WS/WSS 四项
- PPTX Visual Preview Task 7（Important 审查修复）：所有直接 `PptxVisualView` 用例统一由 context manager 在 `finally` shutdown 并等待 profile invalid；真实 `MainWindow` 同样保证异常路径清理
- PPTX Visual Preview Task 7（Minor 审查修复）：fixture/generator/hash 测试移出 `webengine` marker，钉死背景 RGB、`MSO_SHAPE_TYPE.PICTURE` 与 SHA256；Vitest 补充 `data-element-types` 精确断言
- PPTX Visual Preview Task 7（审查验证）：RED `1 failed, 2 passed`，原生 `qtbot.keyClick(QWebEngineView, Right)` 因 WebEngine 焦点桥接 10 秒无事件，按允许的 Minor 留项撤回；其余强化断言直接验证通过。聚焦连续两轮均 `20 passed`；Python 全量 `244 passed`；npm `23 passed`；typecheck/build 与 IDE lint 通过
- PPTX Visual Preview Task 7（审查修复）按本次用户指令创建新提交，不 amend、不 push、不修改 git config
- PPTX Visual Preview Task 8：`reader.spec` 收集完整 `assets/pptx-viewer`（bundle、notice、manifest）并显式收集 `PySide6.QtWebChannel` 隐式模块
- PPTX Visual Preview Task 8：Windows 构建在 Python/PyInstaller 前验证 Node.js 18+ 与 `npm.cmd`，通过 `cmd /d /s /c call` + `Start-Process -Wait -PassThru` 保留原生退出码；含空格 npm 路径与退出码 23 的模拟证明失败时不清理 dist、不运行 PyInstaller
- PPTX Visual Preview Task 8：生产构建依次执行 `npm ci`、包含 typecheck 的 `npm run build`，生成 ordinal 排序的 `manifest.sha256` 并在源 bundle 与 frozen bundle 两次验 hash
- PPTX Visual Preview Task 8：最终 clean build 成功，确认 `dist/Reader/_internal/assets/pptx-viewer/{index.html,manifest.sha256,THIRD_PARTY_NOTICES.txt}`、bundle assets 与 `PySide6/QtWebChannel.pyd` 存在；源/frozen manifest 文件 SHA256 均为 `f6f32aa6416717bb47aebcd4f365cc976dd01c24d86a8e768a12b70042fc2633`
- PPTX Visual Preview Task 8 验证：RED 初始 `4 failed, 13 passed`，另以含空格 npm 路径及 Windows PowerShell `.NET` API 兼容性测试复现两项真实构建问题；GREEN 聚焦 `19 passed`，Python 全量 `251 passed`，最终 `build_windows.ps1` exit 0，IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 8 按本次用户指令只提交、不推送、不修改 git config
- PPTX Visual Preview Task 8（Important）：构建先解析 `npm.cmd`，优先验证其同目录 `node.exe`，仅在不存在时回退 PATH `node.exe`；版本失败消息和正常选择日志均包含实际 Node 路径，避免验证与 npm 执行使用不同安装
- PPTX Visual Preview Task 8（Important/Minor）：source/frozen manifest 共用严格的 SHA256 行格式与空行 guard；测试锁定 Vite `outDir`/`emptyOutDir: true`，显式 opt-in 真实 npm build 证明 stale asset 被删除且自动恢复 bundle，普通 pytest 不调用 npm
- PPTX Visual Preview Task 8（审查验证）：RED `3 failed, 17 passed`；显式 npm 聚焦 `20 passed`；普通全量 `251 passed, 1 skipped`；clean `build_windows.ps1` exit 0 并记录使用 `C:\Program Files\nodejs\node.exe`；同时将既有 Office availability 测试等待条件收紧到最终 tooltip，消除双 queued signal 竞态
- PPTX Visual Preview Task 8（审查修复）按本次用户指令创建新提交，不 amend、不 push、不修改 git config
- PPTX Visual Preview Task 9：新增 `READER_SMOKE_VISUAL_LOG` 可选 JSONL telemetry；`append_visual_ready()` 写入 path/kind/slides/status 后显式 flush + `os.fsync`，默认禁用且无文件副作用
- PPTX Visual Preview Task 9：窗口仅在 document identity、generation、widget、visual mode、layout ownership 与 closing guards 全部通过后记录 ready；关闭 tab 后的迟到 ready 不更新状态也不落盘
- PPTX Visual Preview Task 9：`smoke_windows.ps1` 严格拆分 Phase A/Phase B；Phase A 独立 frozen Reader + 真实四页 fixture + 独立 60 秒 deadline，验证 `visual-ready slides=4` 且无 `renderer-failure`，完整停止 Reader/QtWebEngine 树并删除 visual profile/namespace 后，Phase B 才创建全新 `$ipcPrimary` 执行原有两批 IPC
- PPTX Visual Preview Task 9：AMD/D3D 常驻驱动会长期锁定被重定向 `LOCALAPPDATA` 下的 shader cache；Phase A 因此只复用主机系统 GPU cache 路径，同时继续隔离 Reader/Chromium `USERPROFILE`、`APPDATA`、显式 Chromium user-data-dir、TEMP 与 IPC namespace；Phase B 保持完整 profile 隔离
- PPTX Visual Preview Task 9 验证：RED 聚焦 `5 failed, 3 passed`；GREEN 聚焦 `8 passed`；Web `23 passed`；Python 全量 `255 passed, 1 skipped`；npm typecheck/build、IDE lint、clean PyInstaller build 均通过
- PPTX Visual Preview Task 9 frozen smoke：Phase A 收到真实 fixture `ready/slides=4`，Phase B 精确收到两批各 2 文件 IPC；结束后 `ReaderProcesses=0`、visual/ipc 隔离根均不存在
- PPTX Visual Preview 最终依赖/产物：`pptx-viewer 0.2.2`、lock 解析 `fflate 0.8.3`、Node `22.22.0`、npm `11.15.0`、PySide6 `6.11.2`、PyInstaller `6.22.2`；bundle manifest SHA256 `f6f32aa6416717bb47aebcd4f365cc976dd01c24d86a8e768a12b70042fc2633`
- 最终 `dist/Reader/Reader.exe`：`5884468 bytes`，SHA256 `1a40cb1760499c44d73283895a83752ae0dd4fc84aa96e2412f97dfd9eac0219`；桌面 `Reader.lnk` 已刷新并验证 target/workdir/icon 均指向该 exe
- PPTX Visual Preview Task 9 按本次用户指令只提交、不 push、不修改 git config

## 下一步

1. 用户验收真实日常 PPTX：视觉保真、缩略图/翻页/缩放/适合窗口、缺失字体与单页失败
2. 用户验收“文本模式”回退与可选“Office 高保真”往返切换
3. 若验收发现特定 PPTX 兼容问题，以最小真实 fixture 补充回归后修复

## 接手检查清单

1. 读本文件与当前规格/计划  
2. `git log -15 --oneline` 与 `git status`  
3. 未推送的提交先推送，再改代码  
4. 改完更新本文件的「当前目标 / 已完成 / 下一步」，再提交推送  
